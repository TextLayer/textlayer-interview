from pydantic import Field
from vaul import StructuredOutput
from typing import List, Dict


class SqlQuery(StructuredOutput):
    """A SQL query for retrieving data from a given table."""
    query: str = Field(..., title="A generated SQL query for retrieving data from the table.")
    sql: List[Dict] = Field(..., title="The result of executing the generated SQL query.")