from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery


@tool_call
@observe
def text_to_sql(query: str) -> SqlQuery:
    datastore = DuckDBDatastore(
        database="app/data/data.db"
    )

    result = datastore.execute(query)

    return result.to_markdown(
        index=False, 
        floatfmt=".2f"
        ) if result is not None else ""