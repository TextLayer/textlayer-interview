from app.utils.langfuse_compat import observe
from vaul import tool_call
import pandas as pd
from typing import Optional

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore


@tool_call
@observe
def get_database_schema(table_name: Optional[str] = None) -> str:
    """
    Get database schema information to help with SQL query construction.
    
    Args:
        table_name (Optional[str]): Specific table to get schema for. If None, returns all tables.
    
    Returns:
        str: Formatted schema information including tables, columns, and sample data.
    """
    
    logger.info(f"Getting database schema for table: {table_name or 'all tables'}")
    
    try:
        datastore = DuckDBDatastore(database="app/data/data.db")
        
        if table_name:
            return _get_table_schema(datastore, table_name)
        else:
            return _get_all_tables_schema(datastore)
            
    except Exception as e:
        logger.error(f"Error getting database schema: {e}")
        return f"**Error retrieving schema:** {str(e)}"


def _get_all_tables_schema(datastore: DuckDBDatastore) -> str:
    """Get schema information for all tables."""
    
    try:
        # Get list of all tables
        tables_query = """
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'main'
        ORDER BY table_name
        """
        tables_df = datastore.execute(tables_query)
        
        if tables_df.empty:
            return "**No tables found in the database.**"
        
        schema_info = "# Database Schema Overview\n\n"
        schema_info += f"**Available Tables:** {len(tables_df)} tables found\n\n"
        
        for _, row in tables_df.iterrows():
            table_name = row['table_name']
            schema_info += f"## Table: `{table_name}`\n"
            schema_info += _get_table_details(datastore, table_name)
            schema_info += "\n---\n\n"
        
        return schema_info
        
    except Exception as e:
        return f"**Error getting tables list:** {str(e)}"


def _get_table_schema(datastore: DuckDBDatastore, table_name: str) -> str:
    """Get detailed schema information for a specific table."""
    
    schema_info = f"# Schema for Table: `{table_name}`\n\n"
    schema_info += _get_table_details(datastore, table_name)
    
    return schema_info


def _get_table_details(datastore: DuckDBDatastore, table_name: str) -> str:
    """Get detailed information about a specific table."""
    
    details = ""
    
    try:
        # Get column information
        columns_df = datastore.get_columns(table_name)
        
        if not columns_df.empty:
            details += "### Columns:\n"
            details += columns_df.to_markdown(index=False, tablefmt="pipe")
            details += "\n\n"
        
        # Get row count
        count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
        count_df = datastore.execute(count_query)
        row_count = count_df.iloc[0]['row_count'] if not count_df.empty else 0
        
        details += f"**Total Rows:** {row_count:,}\n\n"
        
        # Get sample data (first 3 rows)
        if row_count > 0:
            sample_df = datastore.get_sample_data(table_name, limit=3)
            if not sample_df.empty:
                details += "### Sample Data (first 3 rows):\n"
                details += sample_df.to_markdown(index=False, tablefmt="pipe", floatfmt=".2f")
                details += "\n\n"
        
        # Get basic statistics for numeric columns
        numeric_stats = _get_numeric_statistics(datastore, table_name)
        if numeric_stats:
            details += numeric_stats
        
    except Exception as e:
        details += f"**Error getting table details:** {str(e)}\n\n"
    
    return details


def _get_numeric_statistics(datastore: DuckDBDatastore, table_name: str) -> str:
    """Get basic statistics for numeric columns."""
    
    try:
        # Get numeric columns
        columns_df = datastore.get_columns(table_name)
        numeric_types = ['INTEGER', 'BIGINT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL', 'FLOAT']
        numeric_columns = columns_df[columns_df['data_type'].isin(numeric_types)]['column_name'].tolist()
        
        if not numeric_columns:
            return ""
        
        stats_info = "### Numeric Column Statistics:\n"
        
        for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
            try:
                stats_query = f"""
                SELECT 
                    '{col}' as column_name,
                    MIN({col}) as min_value,
                    MAX({col}) as max_value,
                    AVG({col}) as avg_value,
                    COUNT(DISTINCT {col}) as distinct_values,
                    COUNT(*) - COUNT({col}) as null_count
                FROM {table_name}
                """
                stats_df = datastore.execute(stats_query)
                
                if not stats_df.empty:
                    row = stats_df.iloc[0]
                    stats_info += f"\n**{col}:**\n"
                    stats_info += f"- Range: {row['min_value']:.2f} to {row['max_value']:.2f}\n"
                    stats_info += f"- Average: {row['avg_value']:.2f}\n"
                    stats_info += f"- Distinct values: {row['distinct_values']:,}\n"
                    if row['null_count'] > 0:
                        stats_info += f"- Null values: {row['null_count']:,}\n"
                        
            except Exception:
                continue  # Skip columns that cause errors
        
        return stats_info + "\n"
        
    except Exception:
        return ""


@tool_call
@observe
def suggest_sql_queries(user_question: str) -> str:
    """
    Suggest SQL query patterns based on the user's question and available schema.
    
    Args:
        user_question (str): The user's natural language question
    
    Returns:
        str: Suggested SQL query patterns and examples
    """
    
    logger.info(f"Suggesting SQL queries for question: {user_question}")
    
    try:
        datastore = DuckDBDatastore(database="app/data/data.db")
        
        # Get available tables
        tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        tables_df = datastore.execute(tables_query)
        
        if tables_df.empty:
            return "**No tables available for query suggestions.**"
        
        table_names = tables_df['table_name'].tolist()
        
        suggestions = f"# SQL Query Suggestions for: \"{user_question}\"\n\n"
        suggestions += f"**Available Tables:** {', '.join(table_names)}\n\n"
        
        # Analyze question for common patterns
        question_lower = user_question.lower()
        
        if any(word in question_lower for word in ['trend', 'over time', 'monthly', 'daily', 'yearly']):
            suggestions += "## Time-based Analysis Patterns:\n"
            suggestions += "```sql\n"
            suggestions += "-- Group by time periods\n"
            suggestions += "SELECT DATE_TRUNC('month', date_column) as month, \n"
            suggestions += "       COUNT(*) as count,\n"
            suggestions += "       AVG(value_column) as avg_value\n"
            suggestions += "FROM table_name \n"
            suggestions += "GROUP BY DATE_TRUNC('month', date_column)\n"
            suggestions += "ORDER BY month;\n"
            suggestions += "```\n\n"
        
        if any(word in question_lower for word in ['top', 'highest', 'largest', 'maximum']):
            suggestions += "## Top/Ranking Patterns:\n"
            suggestions += "```sql\n"
            suggestions += "-- Get top N records\n"
            suggestions += "SELECT column1, column2, value_column\n"
            suggestions += "FROM table_name \n"
            suggestions += "ORDER BY value_column DESC\n"
            suggestions += "LIMIT 10;\n"
            suggestions += "```\n\n"
        
        if any(word in question_lower for word in ['compare', 'vs', 'versus', 'difference']):
            suggestions += "## Comparison Patterns:\n"
            suggestions += "```sql\n"
            suggestions += "-- Compare groups\n"
            suggestions += "SELECT category_column,\n"
            suggestions += "       AVG(value_column) as avg_value,\n"
            suggestions += "       COUNT(*) as count\n"
            suggestions += "FROM table_name \n"
            suggestions += "GROUP BY category_column\n"
            suggestions += "ORDER BY avg_value DESC;\n"
            suggestions += "```\n\n"
        
        if any(word in question_lower for word in ['total', 'sum', 'aggregate']):
            suggestions += "## Aggregation Patterns:\n"
            suggestions += "```sql\n"
            suggestions += "-- Calculate totals and aggregates\n"
            suggestions += "SELECT SUM(amount_column) as total,\n"
            suggestions += "       AVG(amount_column) as average,\n"
            suggestions += "       COUNT(*) as count\n"
            suggestions += "FROM table_name \n"
            suggestions += "WHERE condition;\n"
            suggestions += "```\n\n"
        
        suggestions += "## General Tips:\n"
        suggestions += "- Use `DESCRIBE table_name` to see column details\n"
        suggestions += "- Use `SELECT * FROM table_name LIMIT 5` to see sample data\n"
        suggestions += "- Consider using WHERE clauses to filter data\n"
        suggestions += "- Use appropriate date formats for time-based queries\n"
        
        return suggestions
        
    except Exception as e:
        logger.error(f"Error generating SQL suggestions: {e}")
        return f"**Error generating suggestions:** {str(e)}"
