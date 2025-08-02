from pydantic import Field
from vaul import StructuredOutput


class SqlQuery(StructuredOutput):
    query: str = Field(..., title="A generated SQL query for retrieving data from the table.")