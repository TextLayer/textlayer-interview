from pydantic import Field
from typing import List
from vaul import StructuredOutput


class SqlQuery(StructuredOutput):
    """A SQL query for retrieving data from a given table."""
    query: str = Field(..., title="A generated SQL query for retrieving data from the table.")

class DomainFilter(StructuredOutput):
    """A boolean value indicating whether a column has domain values."""
    has_domain_values: bool = Field(default=False, title="Whether this column contains business domain terms")

class DomainValueRetrieval(StructuredOutput):
    """Structured output for retrieving domain values from vector database."""
    tables: List[str] = Field(default=[], title="A list of tables that contain the domain values.")
    columns: List[str] = Field(default=[], title="A list of columns that contain the domain values.")
    values: List[str] = Field(default=[], title="A list of domain values.")