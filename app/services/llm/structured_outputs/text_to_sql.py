from pydantic import Field, RootModel
from vaul import StructuredOutput
from typing import Dict, List


class SqlQuery(StructuredOutput):
    """A SQL query for retrieving data from a given table."""
    query: str = Field(..., title="A generated SQL query for retrieving data from the table.")

class RelevantColumns(RootModel[Dict[str, List[str]]]):
    """Dynamic table-column mapping where each key is a table name and values are lists of column names."""