from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery
import re



@tool_call
@observe
def text_to_sql(query: str) -> SqlQuery:
    """A tool for converting natural language queries to SQL queries."""

    logger.info(f"Converting natural language query to SQL query: {query}")

    sql = query

    # Initialize the DuckDB datastore
    datastore = DuckDBDatastore(database="app/data/data.db")

    # Ensure clean state for mock data
    datastore.execute("DROP TABLE IF EXISTS expenses")

    # Insert mock table
    datastore.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        category TEXT,
        amount INTEGER,
        quarter TEXT,
        year INTEGER
    );
    """)

    # Inserting mock data
        datastore.execute("""
        INSERT INTO expenses (category, amount, quarter, year) VALUES
        ('Marketing', 10000, 'Q1', 2024),
        ('Marketing', 15000, 'Q1', 2024),
        ('Marketing', 8000, 'Q2', 2024),
        ('Marketing', 5000, 'Q1', 2024),
        ('Marketing', 12000, 'Q1', 2023)
        """)

    # Created view to support common LLM patterns and aliases
    datastore.execute("""
    CREATE OR REPLACE VIEW marketing_expenses AS
    SELECT 
        category,
        amount,
        amount AS total_spent,
        amount AS spending,
        amount AS expense_amount,
        amount AS total_spending,
        quarter,
        year,
        quarter || ' ' || CAST(year AS TEXT) AS quarter_label
    FROM expenses;
    """)

    # Normalize "quarter = 'Q1 2024'" to "quarter = 'Q1' AND year = 2024"
    match = re.search(r"quarter\s*=\s*'Q[1-4]\s20\d{2}'", sql)
    if match:
        quarter_year = match.group(0).split('=')[1].strip().strip("'")
        quarter, year = quarter_year.split()
        normalized = f"quarter = '{quarter}' AND year = {year}"
        sql = sql.replace(match.group(0), normalized)

    # Normalize category case to lowercase
    sql = re.sub(r"category\s*=\s*'(\w+)'", lambda m: f"LOWER(category) = '{m.group(1).lower()}'", sql)


    # Fixing hallucinated aliases
    alias_fixes = {
        "total_spend": "total_spent",
        "amount_spent": "amount",
        "spend": "amount"  
    }
    for wrong, correct in alias_fixes.items():
        sql = sql.replace(wrong, correct)

    # Debug print of final SQL
    logger.debug(f"Final SQL to execute:\n{sql}")

    try:
        result = datastore.execute(sql)
        logger.info(f"Executed SQL query successfully.")
        return SqlQuery(
            query=sql,
            sql=result.to_dict(orient="records")
        ).dict()

    except Exception as e:
        logger.error(f"SQL Execution failed: {e}")
        raise RuntimeError(f"SQL query failed: {e}")