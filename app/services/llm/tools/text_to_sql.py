from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery


@tool_call
@observe
def text_to_sql(sql_query: str) -> SqlQuery:
    """A tool for converting natural language queries to SQL queries."""

    logger.info(f"Converting natural language query to SQL query: {sql_query}")

    # Initialize the DuckDB datastore
    datastore = DuckDBDatastore(
        database="app/data/data.db"
    )

    #debug
    print(f" Debug- Generated sql query: {sql_query}")
    logger.info(f" Debug- Generated sql query: {sql_query}")

    # Execute the query
    result = datastore.execute(sql_query)

    # Return the result
    return result.to_markdown(
        index=False, 
        floatfmt=".2f"
        ) if result is not None else ""