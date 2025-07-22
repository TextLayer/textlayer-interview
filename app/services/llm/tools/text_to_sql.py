"""
Enhanced Text-to-SQL Tool

This tool converts natural language queries to SQL and optionally executes them
against the database. It's designed to work with LiteLLM and includes toggleable
real database access.
"""

from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore


@tool_call
@observe
def text_to_sql(query: str) -> str:
    """Convert natural language query to SQL and execute it against the database."""

    logger.info(f"Processing text-to-SQL query: {query}")

    try:
        # Initialize the DuckDB datastore
        datastore = DuckDBDatastore(database="app/data/data.db")

        # Check if this looks like a SQL query or natural language
        if _is_sql_query(query):
            # Direct SQL execution
            sql_query = query.strip()
            logger.info(f"Executing SQL query: {sql_query}")

            try:
                # Execute the query
                result_df = datastore.execute(sql_query)

                if result_df.empty:
                    return f"""**SQL Query:**
```sql
{sql_query}
```

**Result:** No data found matching the query criteria."""

                # Format results as markdown table
                result_markdown = result_df.to_markdown(index=False, floatfmt=".2f")

                return f"""**SQL Query:**
```sql
{sql_query}
```

**Query Results:**
{result_markdown}

**Summary:** Query returned {len(result_df)} rows."""

            except Exception as e:
                logger.error(f"SQL execution error: {e}")
                return f"""**SQL Query:**
```sql
{sql_query}
```

**Error:** {str(e)}

**Suggestion:** Please check the SQL syntax and table/column names. Available tables: account, customer, product, time, version, time_perspective, other."""

        else:
            # Natural language query - provide guidance
            return f"""**Natural Language Query:** {query}

**Guidance:** Please provide a specific SQL query to execute against the financial database.

**Available Tables:**
- `account` - Financial records (revenue, cost, profit)
- `customer` - Customer information and demographics
- `product` - Product catalog and hierarchy
- `time` - Time dimension (2018-2024, quarters, months)
- `version` - Data version control
- `time_perspective` - Alternative time views
- `other` - Additional dimensional data

**Example SQL for your request:**
```sql
-- Example query structure for your analysis
SELECT
    c.customer_name,
    COUNT(*) as active_months,
    AVG(a.revenue) as avg_revenue,
    STDDEV(a.revenue) / AVG(a.revenue) as coefficient_of_variation
FROM customer c
JOIN account a ON c.customer_id = a.customer_id
JOIN time t ON a.time_id = t.time_id
WHERE a.account_type = 'revenue'
GROUP BY c.customer_id, c.customer_name
HAVING COUNT(*) >= 18
ORDER BY coefficient_of_variation DESC
LIMIT 5;
```

Please provide a complete SQL query to execute."""

    except Exception as e:
        logger.error(f"Error in text_to_sql tool: {e}")
        return f"Error processing query: {str(e)}"


def _is_sql_query(query: str) -> bool:
    """Check if the query looks like SQL."""
    query_upper = query.upper().strip()
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'DROP', 'ALTER']
    return any(query_upper.startswith(keyword) for keyword in sql_keywords)