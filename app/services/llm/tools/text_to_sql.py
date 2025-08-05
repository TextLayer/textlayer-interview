from app.utils.langfuse_compat import observe
from vaul import tool_call
import pandas as pd
import traceback
from typing import Dict, Any

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.structured_outputs.text_to_sql import SqlQuery


@tool_call
@observe
def text_to_sql(query: str) -> str:
    """
    Enhanced tool for executing SQL queries against financial dataset with comprehensive error handling and context.
    
    This tool:
    - Executes SQL queries against the financial database
    - Provides detailed error messages and suggestions
    - Formats results with financial context
    - Includes data validation and quality checks
    """

    logger.info(f"Executing SQL query: {query}")

    try:
        # Initialize the DuckDB datastore
        datastore = DuckDBDatastore(
            database="app/data/data.db"
        )

        # Execute the query
        result = datastore.execute(query)
        
        # Validate and format the result
        if result is None or result.empty:
            return _format_empty_result(query)
        
        # Check for potential data quality issues
        quality_warnings = _check_data_quality(result)
        
        # Format the result with financial context
        formatted_result = _format_financial_result(result, query)
        
        # Combine result with any warnings
        if quality_warnings:
            formatted_result += f"\n\n**Data Quality Notes:**\n{quality_warnings}"
            
        return formatted_result
        
    except Exception as e:
        logger.error(f"Error executing SQL query: {e}")
        return _format_error_response(query, str(e))


def _format_empty_result(query: str) -> str:
    """Format response when query returns no results."""
    return f"""
**Query Result: No Data Found**

The query executed successfully but returned no results. This could mean:
- The specified criteria don't match any records
- The date range might be outside available data
- Table or column names might need adjustment

**Executed Query:** `{query}`

**Suggestions:**
- Try broadening your search criteria
- Check available date ranges
- Verify table and column names
"""


def _format_error_response(query: str, error: str) -> str:
    """Format user-friendly response when query execution fails."""
    
    # Provide helpful, user-friendly responses based on error type
    if "no such table" in error.lower() or "does not exist" in error.lower():
        if "financials" in error.lower():
            return """
**I don't see a 'financials' table in your database.**

Based on your available data, I can help you analyze:

• **Accounts** - Financial account information and calculations
• **Customers** - Customer data with sales managers and channels  
• **Products** - Product lines and inventory
• **Time** - Date ranges and fiscal periods
• **Versions** - Budget and forecast scenarios

**What I can help you analyze:**
- Customer performance by channel or industry
- Product line analysis
- Account structures and hierarchies
- Time-based trends across different periods
- Budget vs forecast comparisons

Would you like me to show you what specific financial analysis is possible with your data structure?
"""
        else:
            return f"""
**I couldn't find that table in your database.**

Let me help you with what's actually available. Your database contains these tables:
• Accounts, Customers, Products, Time, Versions, Other, Time Perspective

Would you like me to show you what analysis I can do with your current data?
"""
    
    elif "no such column" in error.lower():
        return """
**I couldn't find that specific field in your data.**

Let me help you find what you're looking for. Would you like me to:
• Show you the available columns in a specific table?
• Suggest similar analyses I can do with your current data?
• Explain what financial metrics I can calculate?

Just let me know what you're trying to analyze!
"""
    
    else:
        return """
**I had trouble processing that query.**

Let me help you in a different way. I can:
• Show you what tables and data are available
• Suggest specific analyses based on your data structure
• Help you explore your financial data step by step

What would you like to analyze? I'm here to help!
"""


def _check_data_quality(df: pd.DataFrame) -> str:
    """Check for potential data quality issues and return warnings."""
    warnings = []
    
    # Check for null values in key columns
    null_cols = df.columns[df.isnull().any()].tolist()
    if null_cols:
        warnings.append(f"Some columns contain null values: {', '.join(null_cols)}")
    
    # Check for very large or very small numbers that might indicate data issues
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols:
        if df[col].abs().max() > 1e12:
            warnings.append(f"Column '{col}' contains very large values - verify units")
        elif (df[col] != 0).any() and df[col].abs().min() < 1e-6:
            warnings.append(f"Column '{col}' contains very small values - verify precision")
    
    # Check for duplicate rows
    if df.duplicated().any():
        dup_count = df.duplicated().sum()
        warnings.append(f"Dataset contains {dup_count} duplicate rows")
    
    return "\n- ".join([""]+warnings) if warnings else ""


def _format_financial_result(df: pd.DataFrame, query: str) -> str:
    """Format query results in a conversational, user-friendly way."""
    
    row_count = len(df)
    col_count = len(df.columns)
    
    # Create conversational introduction based on query type and results
    intro = _create_conversational_intro(df, query, row_count)
    
    # Format the data in a clean, readable way
    if row_count <= 20 and col_count == 1:
        # For simple lists (like unique values), format as bullet points
        col_name = df.columns[0]
        values = df[col_name].tolist()
        data_display = "\n".join([f"• {value}" for value in values])
    else:
        # For larger datasets or multiple columns, use table format
        data_display = df.to_markdown(
            index=False,
            floatfmt=".2f",
            tablefmt="pipe"
        )
    
    # Add insights for numeric data
    insights = _generate_conversational_insights(df)
    insights_text = f"\n\n{insights}" if insights else ""
    
    # Add the query reference in a friendly way
    query_ref = f"\n\n*I used this query to find the information: `{query}`*"
    
    return f"{intro}\n\n{data_display}{insights_text}{query_ref}"


def _create_conversational_intro(df: pd.DataFrame, query: str, row_count: int) -> str:
    """Create a conversational introduction based on the query and results."""
    
    # Detect query type and create appropriate intro
    query_lower = query.lower()
    col_name = df.columns[0] if len(df.columns) == 1 else "data"
    
    if "distinct" in query_lower or "unique" in query_lower:
        if "industry" in query_lower or "industries" in query_lower:
            return f"**Here are the {row_count} unique industries in your customer data:**"
        elif "product" in query_lower:
            return f"**Here are the {row_count} unique product categories I found:**"
        elif "channel" in query_lower:
            return f"**Here are the {row_count} unique sales channels:**"
        else:
            return f"**Here are the {row_count} unique {col_name.lower()} values I found:**"
    
    elif "count" in query_lower:
        return f"**Here's the count information you requested:**"
    
    elif "top" in query_lower or "limit" in query_lower:
        return f"**Here are the top results I found:**"
    
    elif "sum" in query_lower or "total" in query_lower:
        return f"**Here are the totals I calculated:**"
    
    else:
        return f"**Here's what I found ({row_count} results):**"


def _generate_conversational_insights(df: pd.DataFrame) -> str:
    """Generate conversational insights from the data."""
    insights = []
    row_count = len(df)
    
    # Add contextual insights based on data
    if row_count == 1:
        insights.append("This shows a single result.")
    elif row_count <= 10:
        insights.append(f"I found {row_count} different options for you.")
    elif row_count <= 50:
        insights.append(f"There are {row_count} items in total - quite a good variety!")
    else:
        insights.append(f"That's a substantial dataset with {row_count} records.")
    
    # Add insights for numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        for col in numeric_cols[:2]:  # Limit to first 2 columns
            col_data = df[col].dropna()
            if len(col_data) > 1:
                min_val = col_data.min()
                max_val = col_data.max()
                avg_val = col_data.mean()
                insights.append(f"The {col.lower()} ranges from {min_val:,.0f} to {max_val:,.0f}, with an average of {avg_val:,.0f}.")
    
    return " ".join(insights[:2]) if insights else ""  # Limit to 2 insights


def _generate_insights(df: pd.DataFrame) -> str:
    """Generate basic insights from the data (legacy function)."""
    insights = []
    
    # Check for time-based patterns if date columns exist
    date_cols = df.select_dtypes(include=['datetime64']).columns
    if len(date_cols) > 0:
        date_col = date_cols[0]
        date_range = df[date_col].max() - df[date_col].min()
        insights.append(f"Data spans {date_range.days} days from {df[date_col].min().strftime('%Y-%m-%d')} to {df[date_col].max().strftime('%Y-%m-%d')}")
    
    # Check for significant variations in numeric data
    numeric_cols = df.select_dtypes(include=['number']).columns
    for col in numeric_cols[:2]:  # Limit to first 2 columns
        col_data = df[col].dropna()
        if len(col_data) > 1:
            cv = col_data.std() / col_data.mean() if col_data.mean() != 0 else 0
            if cv > 1:  # High coefficient of variation
                insights.append(f"High variability detected in {col} (CV: {cv:.2f})")
    
    return "\n- ".join([""] + insights[:3]) if insights else ""  # Limit to 3 insights