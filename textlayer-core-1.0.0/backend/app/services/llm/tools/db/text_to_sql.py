from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.db.datastore import SQLiteDatastore


@tool_call
@observe
def text_to_sql(query: str) -> str:
    """Executes a SQL query for SQLite and returns the result as a markdown table.
    Args:
        query (str): The SQL query to execute on the SQLite database.
    Returns:
        str: The result of the SQL query execution, formatted as a markdown table.
    """

    logger.info(f"Converting natural language query to SQL query: {query}")

    # Initialize the DuckDB datastore
    datastore = SQLiteDatastore(database="data/data.db")

    if not query:
        logger.error("No query provided")
        return ""

    # Execute the query
    result = datastore.execute(query)

    # Return the result
    return result.to_markdown(index=False, floatfmt=".2f") if result is not None else ""
