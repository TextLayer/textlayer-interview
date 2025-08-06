from langfuse.decorators import observe
from vaul import tool_call
from flask import current_app
import json

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs.text_to_sql import SqlQuery


@tool_call
@observe
def text_to_sql(natural_language_query: str) -> str:
    """
    A tool for converting natural language queries about finance to SQL queries and executing them.
    
    Args:
        natural_language_query: A natural language question about financial data
        
    Returns:
        Formatted results from the SQL query execution
    """

    logger.info(f"Converting natural language query to SQL: {natural_language_query}")

    # Initialize the DuckDB datastore
    datastore = DuckDBDatastore(database="app/data/data.db")
    
    # Initialize LLM session for SQL generation
    llm_session = LLMSession(
        chat_model=current_app.config.get("CHAT_MODEL"),
        embedding_model=current_app.config.get("EMBEDDING_MODEL"),
    )

    # Create a specialized prompt for text-to-SQL conversion
    sql_generation_prompt = f"""You are a SQL expert specializing in financial data analysis. 

DATABASE SCHEMA:
```sql
-- Main fact table with financial metrics
CREATE TABLE financial_data (
    id INTEGER PRIMARY KEY,
    account_key VARCHAR,        -- Links to account.Key
    customer_key VARCHAR,       -- Links to customer.Key  
    product_key VARCHAR,        -- Links to product.Key
    time_period VARCHAR,        -- Links to time.Key (format: 2018M01, 2018M02, etc.)
    version_key VARCHAR,        -- Links to version.Key (ACT, BUD, FC1)
    time_perspective_key VARCHAR, -- BASE, YTD
    amount DECIMAL(15,2)        -- Financial metric value
);

-- Account dimension (Chart of Accounts)
CREATE TABLE account (
    Key VARCHAR PRIMARY KEY,    -- Account codes
    ParentId VARCHAR,
    Name VARCHAR,               -- Account names like "Gross Revenue", "Product Revenue", "Gross Margin"
    AccountType VARCHAR,        -- Account type codes: "1"=Revenue, "0"=Cost/Expense, "3"=Other, "4"=KPI
    DebitCredit VARCHAR
);

-- Customer dimension
CREATE TABLE customer (
    Key VARCHAR PRIMARY KEY,    -- C1000, C2000, etc.
    ParentId VARCHAR,
    Name VARCHAR,               -- Customer/Region names
    Channel VARCHAR,            -- Distribution channel
    Location VARCHAR,           -- Geographic location
    "Sales Manager" VARCHAR
);

-- Product dimension  
CREATE TABLE product (
    Key VARCHAR PRIMARY KEY,    -- P1000, P10001, etc.
    ParentId VARCHAR,
    Name VARCHAR,               -- Product categories/names (USE THIS, NOT "Product Line")
    "Product Line" VARCHAR      -- Legacy field, prefer using Name
);

-- Time dimension
CREATE TABLE time (
    Month VARCHAR PRIMARY KEY,     -- 2018M01, 2018M02, etc. (links to financial_data.time_period)
    Name VARCHAR,                  -- Month names: January, February, etc.
    StartPeriod VARCHAR,           -- Start date of period
    EndPeriod VARCHAR,             -- End date of period
    Year VARCHAR,                  -- 2018, 2019, etc.
    Quarter VARCHAR,               -- 2018Q1, 2018Q2, etc.
    FiscalQuarterNumber VARCHAR,   -- Quarter numbers
    FiscalMonthNumber VARCHAR,     -- Month numbers
    MonthAbbreviation VARCHAR,     -- Jan, Feb, Mar, etc.
    FiscalMonthAbbreviationWithYear VARCHAR,
    MonthWithYear VARCHAR
);

-- Version dimension
CREATE TABLE version (
    Key VARCHAR PRIMARY KEY,    -- ACT, BUD, FC1
    Name VARCHAR,               -- "Actual", "Budget", "Forecast"
    VersionType VARCHAR         -- Type classification
);
```

CRITICAL SQL REQUIREMENTS:
========================
1. ALWAYS join dimension tables to get descriptive names
2. For revenue analysis: JOIN account table and filter WHERE a.AccountType = '1' (NOT 'Revenue'!)
3. Use p.Name for product categories (NOT p."Product Line")
4. Time JOIN: financial_data fd JOIN time t ON fd.time_period = t.Month (NOT t.Key!)
5. Time filtering: use CAST(t.Year AS INTEGER) for numeric comparisons
6. Quarter extraction: use t.Quarter for quarter-based analysis
7. Growth calculations: use LAG() window functions with proper PARTITION BY and ORDER BY
8. Handle NULL values with NULLIF() in division operations
9. For "past X years": use WHERE CAST(t.Year AS INTEGER) >= (SELECT MAX(CAST(Year AS INTEGER)) - X + 1 FROM time)

QUERY PATTERNS:
==============
Basic revenue by product:
```sql
SELECT p.Name as product_category, SUM(fd.amount) as total_revenue
FROM financial_data fd
JOIN product p ON fd.product_key = p.Key
JOIN account a ON fd.account_key = a.Key
JOIN time t ON fd.time_period = t.Month           -- CORRECT JOIN!
WHERE a.AccountType = '1'                         -- CORRECT FILTER FOR REVENUE!
  AND CAST(t.Year AS INTEGER) = 2018
GROUP BY p.Name
```

Quarterly trends with growth rates:
```sql
WITH quarterly_data AS (
    SELECT 
        p.Name as product_category,
        c.Channel,
        CAST(t.Year AS INTEGER) as year_num,
        t.Quarter,
        SUM(fd.amount) as revenue
    FROM financial_data fd
    JOIN product p ON fd.product_key = p.Key
    JOIN customer c ON fd.customer_key = c.Key
    JOIN time t ON fd.time_period = t.Month         -- CORRECT JOIN!
    JOIN account a ON fd.account_key = a.Key
    WHERE a.AccountType = '1'                       -- CORRECT FILTER FOR REVENUE!
    GROUP BY p.Name, c.Channel, CAST(t.Year AS INTEGER), t.Quarter
)
SELECT 
    product_category,
    Channel,
    year_num,
    Quarter,
    revenue,
    LAG(revenue) OVER (PARTITION BY product_category, Channel ORDER BY year_num, Quarter) as prev_quarter,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY product_category, Channel ORDER BY year_num, Quarter)) 
        / NULLIF(LAG(revenue) OVER (PARTITION BY product_category, Channel ORDER BY year_num, Quarter), 0) * 100, 2
    ) as growth_rate_pct
FROM quarterly_data
ORDER BY product_category, Channel, year_num, Quarter;
```

Time filtering for past 2 years:
```sql
WHERE CAST(t.Year AS INTEGER) >= (SELECT MAX(CAST(Year AS INTEGER)) - 1 FROM time)
```

USER QUERY: {natural_language_query}

Generate a complete, executable SQL query that answers this question. Follow the schema requirements exactly and use proper JOIN syntax. Return only the SQL query without explanations."""

    try:
        # Generate SQL using LLM
        sql_response = llm_session.chat(
            messages=[{"role": "user", "content": sql_generation_prompt}],
            temperature=0.1  # Low temperature for more consistent SQL generation
        )
        
        generated_sql = sql_response.choices[0].message.content.strip()
        
        # Clean up the SQL (remove any markdown formatting)
        if generated_sql.startswith("```sql"):
            generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
        elif generated_sql.startswith("```"):
            generated_sql = generated_sql.replace("```", "").strip()
            
        logger.info(f"Generated SQL: {generated_sql}")

        # Execute the generated SQL
        try:
            result = datastore.execute(generated_sql)
            
            if result is not None and not result.empty:
                # Format the result as markdown table
                formatted_result = result.to_markdown(index=False, floatfmt=".2f")
                
                # Add some context to the result
                result_with_context = f"""**Query**: {natural_language_query}

**Generated SQL**:
```sql
{generated_sql}
```

**Results**:
{formatted_result}

**Summary**: Retrieved {len(result)} record(s) from the financial database."""
                
                return result_with_context
                
            else:
                return f"Query executed successfully but returned no results.\n\nGenerated SQL:\n```sql\n{generated_sql}\n```"
                
        except Exception as e:
            logger.error(f"Error executing generated SQL: {e}")
            return f"Error executing the generated SQL query: {str(e)}\n\nGenerated SQL:\n```sql\n{generated_sql}\n```\n\nPlease try rephrasing your question."
            
    except Exception as e:
        logger.error(f"Error generating SQL from natural language: {e}")
        return f"Error generating SQL query: {str(e)}. Please try rephrasing your question."