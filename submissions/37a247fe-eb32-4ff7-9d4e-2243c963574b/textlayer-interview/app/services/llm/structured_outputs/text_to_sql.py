from pydantic import Field
from vaul import StructuredOutput


class SqlQuery(StructuredOutput):
    """A SQL query for retrieving data from a financial database.
    
    This should contain a valid SQL SELECT statement that can be executed
    against the financial data warehouse tables.
    """
    query: str = Field(
        default="", 
        title="SQL Query",
        description="A complete, valid SQL SELECT statement for querying the financial database. Must be syntactically correct DuckDB SQL.",
        examples=[
            "SELECT Key, Name FROM account WHERE Name LIKE '%Revenue%' ORDER BY Key",
            "SELECT Name FROM customer WHERE ParentId = 'C1000' LIMIT 10",
            "SELECT p1.Name as Parent, p2.Name as Child FROM product p1 JOIN product p2 ON p1.Key = p2.ParentId LIMIT 5"
        ]
    )