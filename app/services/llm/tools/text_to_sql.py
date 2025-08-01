from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery


@tool_call
@observe
def text_to_sql(query: str) -> str:
    """Executes SQL queries against the financial database. 
    You must pass valid SQL strings to this tool — not natural language."""
    
    logger.info(f"Executing SQL query: {query}")
    datastore = DuckDBDatastore(database="app/data/data.db")
    
    try:
        result = datastore.execute(query)
        return result.to_markdown(index=False, floatfmt=".2f") if result is not None else "No data found."
    except Exception as e:
        logger.error(f"SQL Execution Error: {e}")
        return f"Error executing SQL: {str(e)}"