import json
import time
import re
import sqlglot
from sqlglot.errors import ParseError
from typing import Any, Dict

from flask import current_app
from langfuse.decorators import observe
from openai import BadRequestError

from app.errors import ValidationException, ProcessingException
from app import logger
from app.services.llm.session import LLMSession
from app.services.llm.prompts.text_to_sql_prompt import text_to_sql_prompt
from app.services.llm.prompts.sql_rewrite_prompt import sql_rewrite_prompt
from app.services.llm.prompts.select_relevant_column_prompt import select_relevant_column_prompt
from app.services.llm.structured_outputs.text_to_sql import SqlQuery, RelevantColumns
from app.services.datastore.weaviate_retriever import WeaviateRetriever
from app.services.datastore.duckdb_datastore import DuckDBDatastore


class SQLAgentService:
    """
    A service class that handles the text-to-SQL workflow.
    
    This class orchestrates the complete process of converting natural language queries
    to SQL queries and executing them against a database. It includes table retrieval,
    SQL generation using LLM, and query execution with retry mechanisms.
    """
    
    def __init__(
        self, 
        max_retries: int, 
        retry_delay_seconds: float, 
        sql_query_rewrite_attempt: int
        ):
        """
        Initialize the SQLAgentService with configuration and dependencies.

        Args:
            max_retries (int): Maximum number of retry attempts for LLM calls. Defaults to 3.
            retry_delay_seconds (float): Number of seconds to wait between retry attempts. Defaults to 1.0.
        """
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.sql_query_rewrite_attempt = sql_query_rewrite_attempt

        self.llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )

        self.duckdb_datastore = DuckDBDatastore(current_app.config.get("DUCKDB_PATH"))

        self.weaviate_retriever = WeaviateRetriever(
            weaviate_host=current_app.config.get("WV_HTTP_HOST"),
            weaviate_http_port=int(current_app.config.get("WV_HTTP_PORT")),
            weaviate_grpc_port=int(current_app.config.get("WV_GRPC_PORT")),
            )
        self.wv_schema_index = current_app.config.get("WV_SCHEMA_INDEX") 
        self.sql_dilect = current_app.config.get("SQL_DILECT") 
        self.table_top_k = int(current_app.config.get("TABLE_TOP_K"))
        self.column_top_k = int(current_app.config.get("COLUMN_TOP_K"))
        self.row_top_k = int(current_app.config.get("ROW_TOP_K"))

    @observe()
    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Execute the complete text-to-SQL workflow.

        This method orchestrates the entire process: retrieving relevant tables,
        generating SQL from the natural language query, and executing the SQL
        to return results.

        Args:
            user_query (str): The natural language query from the user.

        Returns:
            Dict[str, str]: A dictionary containing:
                - "SQL Query from User Question": The generated SQL query
                - "Retrieved Data from the SQL Database": The query results

        Raises:
            ValidationException: If the user query is invalid or LLM response parsing fails.
            ProcessingException: If table retrieval or SQL execution fails.
        """
        if not user_query or not user_query.strip():
            sql_query = "No SQL Query generated since no user query was provided"
            sql_result = "No data was retrieved from the database since no user query was provided"
        else:
            query_vector = self._generate_user_query_vector(user_query)
            table_names, tables_context = self._retrieve_tables(user_query, query_vector)
            relevant_columns_dict = self._select_columns_from_schema(user_query, tables_context)
            column_context = self._retrieve_columns(relevant_columns_dict, query_vector)
            row_context = self._retrieve_rows(table_names, query_vector)
            context = self._context_generator(tables_context, column_context, row_context)
            sql_query = self._generate_sql(user_query, context)
            sql_query_rewrite = self._sql_query_rewrite(
                                        sql_query=sql_query, 
                                        user_query=user_query, 
                                        table_context=tables_context
                                    )
            sql_result = self._execute_sql(sql_query_rewrite)
            self.weaviate_retriever.close()
            self.duckdb_datastore.close()

        return {
            "SQL Query from User Question": sql_query,
            "Retrieved Data from the SQL Database": sql_result,
        }
    
    @observe()
    def _context_generator(self, tables_context:str, column_context:str, row_context:str) -> str:
        context = tables_context
        if column_context or row_context:
            context += "\n\nThe following are sample data from rows and columns in the tables above to help you generate the SQL Query better\n"
            context += column_context + "\n" + row_context
        return context

    @observe()
    def _generate_user_query_vector(self, user_query: str) -> list:
        try:
            query_vector = self.llm_session.generate_embedding(user_query)
        except BadRequestError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to fetch query vector: {e}")
            raise ValidationException("Error in fetching query vector")
        return query_vector


    @observe()
    def _retrieve_tables(self, user_query: str, query_vector: list) -> str:
        """
        Retrieve relevant database tables based on the user query.

        Uses semantic search to find the most relevant tables for the given
        natural language query.

        Args:
            user_query (str): The natural language query to find relevant tables for.

        Returns:
            str: A formatted string containing the context of relevant tables
                 with their descriptions and column information.
            str: A list of the names of the retireved tables

        Raises:
            ProcessingException: If table retrieval fails due to internal errors.
        """
        try:
            schema_results = self.weaviate_retriever.query_collection(
                class_name=self.wv_schema_index,
                query_vector=query_vector,
                top_k=self.table_top_k
            )
            retrieved_table_context = self._build_context_from_results(schema_results)
            retrieved_table_names = [node.properties.get("table", "") for node in schema_results]
            logger.debug(f"Retrieved Tables:\n {[node.properties.get("table", "") for node in schema_results]}")
            logger.debug(f"Retrieved Context:\n {retrieved_table_context}")
        except Exception as e:
            logger.error(f"Error retrieving tables: {e}")
            raise ProcessingException(f"Failed to retrieve relevant tables: {e}")
        return retrieved_table_names, retrieved_table_context
    
    @observe()
    def _select_columns_from_schema(self, user_query: str, table_context: str) -> str:
        """
        Select relevant columns from table schema using LLM.

        Args:
            user_query (str): User's natural language query.
            table_context (str): Table schema context to analyze.

        Returns:
            dict: Mapping of table names to lists of relevant column names.

        Raises:
            ValidationException: If LLM response parsing fails.
            BadRequestError: If LLM service returns bad request.
        """
        prompt = select_relevant_column_prompt(
            table_context=table_context,
            query_str=user_query,
        )
        try:
            response = self.llm_session.chat([{"role": "user", "content": prompt}])
            content = response.choices[0].message.content.strip()
            try:
                parsed = RelevantColumns(**json.loads(content))
                parsed_dict = parsed.root
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                raise ValidationException("Error in parsing LLM response.")
        except BadRequestError as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to fetch chat response: {e}")
            raise ValidationException("Error in fetching chat response.")        
        logger.debug(f"Retrieved Context:\n {parsed}")
        return parsed_dict
    
    @observe()
    def _retrieve_columns(self, relevant_columns_dict: dict, query_vector: list):
        relevant_columns_collections = self._generate_column_index_names(relevant_columns_dict)
        if not relevant_columns_collections:
            return ""
        column_retrieval_results = []
        try:
            for collection_name in relevant_columns_collections:
                col_results = self.weaviate_retriever.query_collection(
                    class_name=collection_name,
                    query_vector=query_vector,
                    top_k=self.column_top_k
                )
                column_retrieval_results.append(col_results)

            column_context = self._build_rows_or_columns_context(column_retrieval_results)
            logger.debug(f"Retrieved Columns Context:\n {column_context}")
        except Exception as e:
            logger.error(f"Error retrieving columns: {e}")
            raise ProcessingException(f"Failed to retrieve columns: {e}")
        return column_context
    

    @observe()
    def _retrieve_rows(self, table_names: list[str], query_vector: list) -> str:
        """
        Retrieve relevant rows from specified tables using Weaviate vector search.

        Performs semantic search across row-level data in the specified tables using
        the provided query vector. Queries each table's row collection in Weaviate
        and aggregates the results into a formatted context string.

        Args:
            table_names (list[str]): List of table names to search for relevant rows.
            query_vector (list): The embedding vector of the user query for semantic search.

        Returns:
            str: A formatted string containing the context of relevant rows from all tables,
                or an empty string if no table names are provided.

        Raises:
            ProcessingException: If row retrieval fails due to Weaviate connection issues
                            or other internal errors.

        Example:
            >>> table_names = ["product", "customer"]
            >>> query_vector = [0.1, 0.2, 0.3, ...]
            >>> context = self._retrieve_rows(table_names, query_vector)
            >>> print(context)
            "Row from table 'product': (Key='P1000', Name='Product A', ...)
            Row from table 'customer': (Key='C1000', Name='Customer A', ...)"
        """
        if not table_names:
            return ""

        row_retrieval_results = []
        try:
            for table in table_names:
                table_collection_name = self.sanitize_name(f"table_{table}")
                row_results = self.weaviate_retriever.query_collection(
                    class_name=table_collection_name,
                    query_vector=query_vector,
                    top_k=self.row_top_k
                )
                row_retrieval_results.append(row_results)

                row_context = self._build_rows_or_columns_context(row_retrieval_results)
                logger.debug(f"Retrieved Rows Context:\n {row_context}")
        except Exception as e:
            logger.error(f"Error retrieving rows: {e}")
            raise ProcessingException(f"Failed to retrieve rows: {e}")
        return row_context

    @observe()
    def _generate_sql(self, user_query: str, table_context: str) -> str:
        """
        Generate a SQL query from natural language using LLM.

        Creates a prompt with the user query and table context, then uses
        the LLM to generate a SQL query. Implements retry logic for robustness.

        Args:
            user_query (str): The natural language query to convert to SQL.
            table_context (str): The context string containing relevant table schemas.

        Returns:
            str: The generated SQL query.

        Raises:
            ValidationException: If LLM response parsing fails after all retry attempts.
            BadRequestError: If the LLM service returns a bad request error.
        """
        prompt = text_to_sql_prompt(
        dialect=self.sql_dilect,
        table_context=table_context,
        query_str=user_query,
        )

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.llm_session.chat([{"role": "user", "content": prompt}])
                content = response.choices[0].message.content.strip()

                # Try to parse JSON
                try:
                    parsed = SqlQuery(**json.loads(content))
                    # Check SQL syntax
                    if self._is_sql_syntax_valid(parsed.query):
                        return parsed.query
                    else:
                        if attempt < self.max_retries:
                            logger.warning(f"Attempt {attempt}: Invalid SQL syntax from LLM. Query: {parsed.query}. Retrying...")
                            time.sleep(self.retry_delay_seconds)
                            continue
                        else:
                            logger.error(f"Failed to generate valid SQL syntax after {self.max_retries} attempts")
                            raise ValidationException("Invalid SQL syntax from LLM after multiple retries")
                except json.JSONDecodeError as e:
                    if attempt < self.max_retries:
                        logger.warning(
                        f"Attempt {attempt}: Invalid JSON from LLM. Content: {repr(content)}. Retrying..."
                        )
                        time.sleep(self.retry_delay_seconds)
                        continue
                    else:
                        logger.error(f"Failed to parse JSON after {self.max_retries} attempts: {e}")
                        raise ValidationException("Error in parsing LLM response.")

            except BadRequestError as e:
                raise e

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"Attempt {attempt}: Failed to fetch chat response: {e}")
                    time.sleep(self.retry_delay_seconds)
                    continue
                else:
                    logger.error(f"Failed to fetch chat response after {self.max_retries} attempts: {e}")
                    raise ValidationException("Error in fetching chat response.")

    @observe()
    def _sql_query_rewrite(self, sql_query: str, user_query: str, table_context: str) -> str:
        """
        Makes an LLM call and shared the already generated SQL Query with the LLM 
        together with the original user query and table schema and asks the LLM 
        to review and if needed modify the query.
        
        Args:
            sql_query (str): The initial SQL query to be rewritten.
            user_query (str): The original natural language query.
            table_context (str): The context string containing relevant table schemas.
            
        Returns:
            str: The rewritten SQL query.
            
        Raises:
            ValidationException: If LLM response parsing fails after all retry attempts.
            BadRequestError: If the LLM service returns a bad request error.
        """
        current_sql_query = sql_query

        sql_rewrite_attempt = self.sql_query_rewrite_attempt
        for attempt in range(1, sql_rewrite_attempt + 1):
            prompt = sql_rewrite_prompt(
            dialect=self.sql_dilect,
            table_context=table_context,
            query_str=user_query,
            sql_query = current_sql_query,
            )
            try:
                response = self.llm_session.chat([{"role": "user", "content": prompt}])
                content = response.choices[0].message.content.strip()
                try:
                    parsed = SqlQuery(**json.loads(content))
                    # Check SQL syntax
                    if self._is_sql_syntax_valid(parsed.query):
                        current_sql_query = parsed.query
                    else:
                        logger.warning(f"SQL rewrite attempt {attempt}: Invalid SQL syntax. Keeping previous query.")
                        # Keeping previous query

                except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON from SQL rewrite at attempts {attempt}: {e}")
                        # Keeping previous query
            except BadRequestError as e:
                logger.warning(f"BadRequestError: Failed to get chat response for SQL rewrite attempt {attempt}: {e}")
                # Keeping previous query
            except Exception as e:
                logger.warning(f"ValidationException: Failed to get chat response for SQL rewrite attempt {attempt}: {e}")
                # Keeping previous query

        return current_sql_query


    @observe()
    def _execute_sql(self, sql_query: str) -> str:
        """
        Execute a SQL query against the database.

        Args:
            sql_query (str): The SQL query to execute.

        Returns:
            str: The result of the SQL query execution.

        Raises:
            ProcessingException: If SQL execution fails due to database errors.
        """
        try:
            result = self.duckdb_datastore.execute(sql_query)
            reuslt_str = result.to_string(index=False).strip()
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            raise ProcessingException(f"Failed to execute SQL query: {e}")
        # return result[0].metadata["result"]
        return reuslt_str

    def _build_context_from_results(self, results: list) -> str:
        """
        Generate context string from Weaviate table search results.

        Extracts the 'content' property from each Weaviate object and formats
        them into a bulleted list context string.

        Args:
            results (list): List of Weaviate objects with 'properties.content' attribute.

        Returns:
            str: Formatted context string with each table info prefixed with "- ",
                or "No related tables/data found" if results is empty.
        """
        if results:
            context_lines = []
            for result in results:
                try:
                    table_info = result.properties["content"]
                    context_lines.append("- " + table_info)
                except Exception as e:
                    logger.error("Failed generating context for tables")
            context = "\n".join(context_lines)
        else:
            context = "No related tables/data found"
        return context
    
    def _build_rows_or_columns_context(self, weaviate_rows_or_columns_results: list):
        """
        Build a formatted context string from Weaviate search results.

        Processes nested lists of Weaviate objects containing row or column data
        and extracts the 'content' property from each object to create a
        formatted context string. This function handles the nested structure
        where each index contains multiple Weaviate objects.

        Args:
            weaviate_rows_or_columns_results (list): A nested list structure where:
                - Outer list contains results from different Weaviate collections
                - Inner lists contain Weaviate objects with 'properties' attribute
                - Each Weaviate object has a 'content' property containing the data

        Returns:
            str: A formatted string with each row/column context on a new line,
                or an empty string if no results are provided.
        """
        if not weaviate_rows_or_columns_results:
            return ""
        row_or_column_context_lines = []
        for result_from_one_index in weaviate_rows_or_columns_results:
            for retireved_row_or_col in result_from_one_index:
                try:
                    row_or_column_info = retireved_row_or_col.properties["content"]
                    row_or_column_context_lines.append(row_or_column_info)
                except Exception as e:
                    logger.error("Failed generating context for row/column")
        row_or_col_context = "\n".join(row_or_column_context_lines)
        return row_or_col_context
    
    def _generate_column_index_names(self, relevant_columns_dict: dict):
        """
        This function generates weaviate collection names from a dictionary of tables(keys) and list of columns (values)
        """

        if not relevant_columns_dict:
            logger.info("LLM returned an empty result for relevant columns to the user query")
            return []

        column_collection_names = []

        for table_name, columns in relevant_columns_dict.items():
            if not columns:
                continue
            for column in columns:
                name = self.sanitize_name(f"table_{table_name}_{column}")
                column_collection_names.append(name)
        return column_collection_names
    
    @staticmethod
    def sanitize_name(name: str):
        return re.sub(r'\W|^(?=\d)', '_', name)

    def _format_table_context(self, tables: list) -> str:
        """
        Format retrieved table information into a context string.

        Converts a list of table objects into a formatted string that can be
        used as context for the LLM prompt.

        Args:
            tables (list): List of table objects with metadata containing table information.

        Returns:
            str: A formatted string containing table names and descriptions,
                 or "No related tables/data found" if the list is empty.
        """
        if tables:
            context_lines = []
            for table in tables:
                table_info = table.metadata["table_name"]
                table_info += f" The table description is: {table.metadata["table_context"]}"
                context_lines.append("- " + table_info)
            context = "\n".join(context_lines)
        else:
            context = "No related tables/data found"
        return context

    def _is_sql_syntax_valid(self, query: str) -> bool:
        """
        Validate SQL syntax using sqlglot parser for the specific database dialect.
        
        Args:
            query (str): The SQL query to validate.
            
        Returns:
            bool: True if SQL syntax is valid, False otherwise.
        """
        try:
            sqlglot.parse_one(query)
            return True
        except ParseError:
            return False

def run_sql_workflow_sync(user_query: str) -> Dict[str, Any]:
    """
    Synchronous wrapper function to run the SQL workflow.

    This function creates a SQLAgentService instance with configuration from
    the Flask app context and executes the complete text-to-SQL workflow.

    Args:
        user_query (str): The natural language query to process.

    Returns:
        Dict[str, Any]: A dictionary containing the generated SQL query and its results.

    Raises:
        ValidationException: If the user query is invalid or LLM response parsing fails.
        ProcessingException: If table retrieval or SQL execution fails.
        RuntimeError: If required configuration is not available in Flask app context.
    """
    service = SQLAgentService(
        max_retries=int(current_app.config.get("MAX_RETRIES")),
        retry_delay_seconds=float(current_app.config.get("RETRY_DELAY_SECONDS")),
        sql_query_rewrite_attempt=int(current_app.config.get("SQL_QUERY_REWRITE_ATTEMPT")),
    )
    return service.run(user_query)