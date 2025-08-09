from langfuse.decorators import observe
from openai.resources.containers.files import content
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery
from app.services.llm.session import LLMSession
from app.utils.duckdb_utils import (
    load_table_examples,
    load_table_schema,
    VALID_DATETIME_FUNCTIONS,
)
from app.services.rag.rag_inference import rag_index_retrieve
from flask import current_app

SQL_GENERATION_PROMPT = f"""
    You are a helpful agent assistant named specializing in conert user natural language input queries in DuckDB SQL dialect queries.
    
    ***Context:
    * The following is context regarding the database, the first set is a CSV of the schema, the second set is a set of example of
    non null and non empty rows of values from each table
    {load_table_schema()}
    
    {load_table_examples()}
    
    Note: when processing fields that contain datetime strings, some of them maybe NULL or "", adjust SQL query to remove those rows
    valid DUckDB SQL datetime functions are {VALID_DATETIME_FUNCTIONS}
    ***Actions:
    General instructions:
    1. if user query is completely irrelevant and not a question related the dataset politely ask the user to enter the query again
    2. if a user is querying something from a database but the query is ambiguous or misspecified a table name or column ask a clarifying question
    3. If the user query is clearly relevant to querying a database output a valid SQL query
    6. Politely refuse any user query that makes write operations to the database, assume the database is read only
    
    Query few shot examples that map user queries to sql queries for specific cases are below:
    %nodes
    
    # SQL Specific Instructions:
    1. In aggregation operations involving booleans, remove rows that have 'NA', Null or '' entries
    Output instructions:
    1. Output a valid SQL query in a single line, no line breaks
    
    """


SUMMARIZIER_PROMPT = """
You are given a output of a SQL query in markdown and a original user input that was converted to SQL query.
SQL query output: %sql_output
User input query: %user_query
Use the sql query output to answer the question in the user input, be as concise as possible, two sentences max.
If  SQL query output  is null answer with "Sorry, there was an error try again".
"""


def prepare_messages(sql_output: str, user_query: str) -> list:
    messsages = [
        {
            "role": "system",
            "content": SUMMARIZIER_PROMPT.replace("%sql_output", sql_output).replace(
                "%user_query", user_query
            ),
        },
    ]
    return messsages


@tool_call
@observe
def text_to_sql_tool(user_query: str) -> str:
    """A tool for executing SQL queries and summarizing answers.
    user_query user input"""

    # execute RAG query
    nodes = None

    # try RAG retrieval, soft error if fail
    try:
        nodes = rag_index_retrieve(user_query)
    except Exception as e:
        logger.error(f"Cannot execture RAG call in text_to_sql_tool() {e}")

    llm = LLMSession(
        chat_model=current_app.config.get("O3_MINI_MODEL"),
        embedding_model=current_app.config.get("EMBEDDING_MODEL"),
    )
    logger.info(f"Converting natural language query to SQL query: {user_query}")
    system_message = [
        {
            "role": "system",
            "content": SQL_GENERATION_PROMPT.replace("%nodes", str(nodes)),
        },
        {"role": "user", "content": user_query},
    ]
    response = llm.chat(system_message)
    logger.info(f"\n\ngenerated SQL query {response.choices[0]['message']['content']}")
    # Initialize the DuckDB datastore
    # DANGER:  read_only=True must be set or user/LLM can potentially delete or overwrite data
    # read_only=True is set
    datastore = DuckDBDatastore(database="app/data/data.db")

    # Execute the query
    result = datastore.execute(response.choices[0]["message"]["content"])

    # Return the result
    sql_result_markdown = (
        result.to_markdown(index=False, floatfmt=".2f") if result is not None else ""
    )

    llm_summarizier = LLMSession(
        chat_model=current_app.config.get("CHAT_MODEL"),
        embedding_model=current_app.config.get("EMBEDDING_MODEL"),
    )
    response = llm_summarizier.chat(prepare_messages(sql_result_markdown, user_query))

    return f"{sql_result_markdown}\n\n__{response.choices[0]['message']['content']}__"
