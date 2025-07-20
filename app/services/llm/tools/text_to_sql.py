from langfuse.decorators import observe
from vaul import tool_call
from typing import Dict

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.tools.sql_generator import generate_sql_from_prompt

@tool_call
@observe()
def text_to_sql(user_query: str, schema_info: Dict) -> Dict:
    """
    Converts a user query to SQL using an LLM-based generator, then executes the SQL
    against a DuckDB database and returns the results.

    Args:
        user_query (str): The user's question (in natural language or SQL).
        schema_info (Dict): The inferred database schema context.

    Returns:
        Dict: Result status, original query, generated SQL, and results in markdown.
    """
    try:
        # Always generate SQL via LLM (assumes prior classification already handled direct SQL cases)
        result = generate_sql_from_prompt(user_query, schema_info)
        query = result.get("query", "")

        if not query:
            return {
                "status": "error",
                "user_query": user_query,
                "sql_query": "N/A",
                "error_message": "Sorry, I couldn't generate a SQL query.",
                "natural_language_answer": "I couldn't understand the question well enough to generate a SQL query."
            }

        # Execute the generated SQL query
        datastore = DuckDBDatastore("app/data/data.db")
        df = datastore.execute(query)

        if df is not None and not df.empty:
            result_md = df.to_markdown(index=False)
            return {
                "status": "success",
                "user_query": user_query,
                "sql_query": query,
                "result_markdown": result_md,
                "natural_language_answer": f"Here is the result for your question:\n\n{result_md}"
            }
        else:
            return {
                "status": "success",
                "user_query": user_query,
                "sql_query": query,
                "result_markdown": "No results found.",
                "natural_language_answer": "I ran the query but found no matching results."
            }

    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        return {
            "status": "error",
            "user_query": user_query,
            "sql_query": query if 'query' in locals() else "N/A",
            "error_message": str(e),
            "natural_language_answer": "There was an error executing your query. Please try a different question."
        }


