"""
Enhanced text-to-SQL tool with validation and schema awareness.
"""
import json
import pandas as pd
from typing import Dict, Any, Optional
from flask import current_app
from vaul import tool_call
from langfuse.decorators import observe

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.datastore.schema_inspector import SchemaInspector
from app.services.llm.session import LLMSession


class SqlQueryValidator:
    """Validates SQL queries for safety and correctness."""
    
    DANGEROUS_KEYWORDS = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE',
        'EXEC', 'EXECUTE', 'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
    ]
    
    @staticmethod
    def is_safe_query(query: str) -> tuple[bool, str]:
        """
        Check if a SQL query is safe to execute (read-only).
        
        Returns:
            tuple: (is_safe, error_message)
        """
        query_upper = query.upper().strip()
        
        # Check for dangerous keywords
        for keyword in SqlQueryValidator.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                return False, f"Query contains dangerous keyword: {keyword}"
        
        # Must start with SELECT
        if not query_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check for semicolon (potential SQL injection)
        if ';' in query and not query.strip().endswith(';'):
            return False, "Multiple statements not allowed"
        
        return True, ""
    
    @staticmethod
    def validate_syntax(query: str, datastore: DuckDBDatastore) -> tuple[bool, str]:
        """
        Validate SQL syntax by attempting to explain the query.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Use EXPLAIN to validate syntax without executing
            explain_query = f"EXPLAIN {query}"
            datastore.execute(explain_query)
            return True, ""
        except Exception as e:
            return False, f"SQL syntax error: {str(e)}"


@tool_call
@observe
def enhanced_text_to_sql(query: str) -> str:
    """
    Enhanced tool for converting natural language queries to SQL with validation and context awareness.
    
    Args:
        query: Natural language query about financial data
        
    Returns:
        str: Formatted results with analysis or error message
    """
    
    logger.info(f"Processing enhanced text-to-SQL query: {query}")
    
    try:
        # Initialize components
        datastore = DuckDBDatastore(database="app/data/data.db")
        schema_inspector = SchemaInspector(database_path="app/data/data.db")
        
        # Get schema context and relevant tables
        schema_context = schema_inspector.get_schema_context_for_prompt()
        relevant_tables = schema_inspector.get_relevant_tables_for_query(query)
        
        # Generate SQL using LLM with enhanced context
        sql_query = _generate_sql_with_context(
            query, schema_context, relevant_tables
        )
        
        if not sql_query:
            return "Error: Could not generate SQL query from your request."
        
        # Validate the generated SQL
        is_safe, safety_error = SqlQueryValidator.is_safe_query(sql_query)
        if not is_safe:
            logger.warning(f"Unsafe SQL query blocked: {safety_error}")
            return f"Security Error: {safety_error}"
        
        is_valid, syntax_error = SqlQueryValidator.validate_syntax(sql_query, datastore)
        if not is_valid:
            logger.warning(f"Invalid SQL syntax: {syntax_error}")
            return f"SQL Error: {syntax_error}"
        
        # Execute the validated query
        logger.info(f"Executing validated SQL: {sql_query}")
        result_df = datastore.execute(sql_query)
        
        if result_df is None or result_df.empty:
            return "No Results: Your query returned no data. This might be due to:\n- No matching records in the database\n- Filters that are too restrictive\n- Date ranges outside available data"
        
        # Format results with analysis
        return _format_results_with_analysis(result_df, sql_query, query)
        
    except Exception as e:
        logger.error(f"Error in enhanced_text_to_sql: {e}")
        return f"System Error: An error occurred while processing your query: {str(e)}"


def _generate_sql_with_context(
    natural_query: str, 
    schema_context: str, 
    relevant_tables: list
) -> Optional[str]:
    """
    Generate SQL query using LLM with enhanced context.
    """
    try:
        llm_session = LLMSession(
            chat_model=current_app.config.get("CHAT_MODEL"),
            embedding_model=current_app.config.get("EMBEDDING_MODEL"),
        )
        
        # Create focused prompt for SQL generation
        sql_prompt = f"""
You are a SQL expert. Convert the following natural language query to a precise SQL query.

## Database Schema:
{schema_context}

## Relevant Tables:
{', '.join(relevant_tables) if relevant_tables else 'All tables available'}

## User Query:
{natural_query}

## Instructions:
1. Generate ONLY a SELECT query (no modifications allowed)
2. Use proper SQL syntax for DuckDB
3. Include appropriate WHERE clauses for filtering
4. Use meaningful column aliases
5. Consider using LIMIT for large result sets
6. Format dates properly if needed
7. Handle NULLs appropriately

## Response Format:
Return ONLY the SQL query, no explanation or markdown formatting.

SQL Query:"""

        messages = [{"role": "user", "content": sql_prompt}]
        
        response = llm_session.chat(messages=messages)
        sql_query = response.choices[0].message.content.strip()
        
        # Clean up the response (remove markdown formatting if present)
        if sql_query.startswith('```'):
            lines = sql_query.split('\n')
            sql_query = '\n'.join(lines[1:-1]) if len(lines) > 2 else sql_query
        
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        return sql_query
        
    except Exception as e:
        logger.error(f"Error generating SQL with context: {e}")
        return None


def _format_results_with_analysis(result_df, sql_query: str, original_query: str) -> str:
    """
    Format query results with business analysis and insights.
    """
    try:
        # Basic statistics
        row_count = len(result_df)
        col_count = len(result_df.columns)
        
        # Start building the response
        response_parts = [
            f"Query Results ({row_count:,} rows, {col_count} columns)",
            ""
        ]
        
        # Add the data table (limit display for readability)
        display_limit = 10
        if row_count <= display_limit:
            response_parts.append("Data:")
            response_parts.append(result_df.to_markdown(index=False, floatfmt=".2f"))
        else:
            response_parts.append(f"Data (showing first {display_limit} rows):")
            response_parts.append(result_df.head(display_limit).to_markdown(index=False, floatfmt=".2f"))
            response_parts.append(f"\n... and {row_count - display_limit:,} more rows")
        
        response_parts.append("")
        
        # Add summary statistics for numeric columns
        numeric_cols = result_df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            response_parts.append("Summary Statistics:")
            for col in numeric_cols:
                if not result_df[col].isna().all():
                    total = result_df[col].sum()
                    avg = result_df[col].mean()
                    min_val = result_df[col].min()
                    max_val = result_df[col].max()
                    
                    # Format monetary values
                    if 'amount' in col.lower() or 'balance' in col.lower() or 'value' in col.lower():
                        response_parts.append(f"- {col}: Total: ${total:,.2f}, Avg: ${avg:,.2f}, Range: ${min_val:,.2f} to ${max_val:,.2f}")
                    else:
                        response_parts.append(f"- {col}: Total: {total:,.2f}, Avg: {avg:.2f}, Range: {min_val:.2f} to {max_val:.2f}")
            response_parts.append("")
        
        # Add insights based on the data
        insights = _generate_insights(result_df, original_query)
        if insights:
            response_parts.append("Key Insights:")
            response_parts.extend(insights)
            response_parts.append("")
        
        # Add technical details
        response_parts.append("Technical Details:")
        response_parts.append(f"- SQL Query: `{sql_query}`")
        response_parts.append(f"- Execution: Successful")
        response_parts.append(f"- Data Quality: {_assess_data_quality(result_df)}")
        
        return "\n".join(response_parts)
        
    except Exception as e:
        logger.error(f"Error formatting results: {e}")
        return result_df.to_markdown(index=False, floatfmt=".2f")


def _generate_insights(result_df, original_query: str) -> list:
    """Generate business insights from the query results."""
    insights = []
    
    try:
        row_count = len(result_df)
        
        # Volume insights
        if row_count == 0:
            insights.append("- No data found matching your criteria")
        elif row_count == 1:
            insights.append("- Single record found - this might be a specific lookup")
        elif row_count < 10:
            insights.append(f"- Small dataset ({row_count} records) - detailed analysis possible")
        elif row_count < 100:
            insights.append(f"- Moderate dataset ({row_count} records) - good for trend analysis")
        else:
            insights.append(f"- Large dataset ({row_count:,} records) - suitable for statistical analysis")
        
        # Analyze numeric columns for patterns
        numeric_cols = result_df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if not result_df[col].isna().all():
                # Check for outliers (simple method)
                q75, q25 = result_df[col].quantile([0.75, 0.25])
                iqr = q75 - q25
                outlier_threshold = 1.5 * iqr
                outliers = result_df[(result_df[col] < (q25 - outlier_threshold)) | 
                                   (result_df[col] > (q75 + outlier_threshold))]
                
                if len(outliers) > 0:
                    insights.append(f"- {len(outliers)} potential outliers detected in {col}")
                
                # Check for zero/negative values in amount fields
                if 'amount' in col.lower() and (result_df[col] <= 0).any():
                    zero_count = (result_df[col] == 0).sum()
                    negative_count = (result_df[col] < 0).sum()
                    if zero_count > 0:
                        insights.append(f"- {zero_count} zero-value transactions in {col}")
                    if negative_count > 0:
                        insights.append(f"- {negative_count} negative values in {col} (refunds/reversals?)")
        
        # Date-based insights
        date_cols = result_df.select_dtypes(include=['datetime64', 'object']).columns
        for col in date_cols:
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    date_series = pd.to_datetime(result_df[col], errors='coerce')
                    if not date_series.isna().all():
                        date_range = date_series.max() - date_series.min()
                        insights.append(f"- Data spans {date_range.days} days from {date_series.min().strftime('%Y-%m-%d')} to {date_series.max().strftime('%Y-%m-%d')}")
                except:
                    pass
        
    except Exception as e:
        logger.warning(f"Error generating insights: {e}")
    
    return insights


def _assess_data_quality(result_df) -> str:
    """Assess basic data quality metrics."""
    try:
        total_cells = result_df.size
        null_cells = result_df.isna().sum().sum()
        null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0
        
        if null_percentage == 0:
            return "Excellent (no missing values)"
        elif null_percentage < 5:
            return f"Good ({null_percentage:.1f}% missing values)"
        elif null_percentage < 15:
            return f"Fair ({null_percentage:.1f}% missing values)"
        else:
            return f"Poor ({null_percentage:.1f}% missing values)"
    except:
        return "Unknown"
