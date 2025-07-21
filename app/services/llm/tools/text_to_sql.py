from langfuse.decorators import observe
from vaul import tool_call

from app import logger
from app.services.datastore.duckdb_datastore import DuckDBDatastore
from app.services.llm.session import LLMSession
from app.services.llm.structured_outputs.text_to_sql import SqlQuery
from flask import current_app
import re
import pandas as pd


@tool_call
@observe
def text_to_sql(natural_language_query: str) -> str:
    """
    A tool for converting natural language queries to SQL queries and executing them.
    
    Args:
        natural_language_query (str): The natural language question about the financial data
        
    Returns:
        str: The result of the SQL query with analysis, or an error message
    """
    
    logger.info(f"Converting natural language query to SQL: {natural_language_query}")
    
    # Initialize the DuckDB datastore
    datastore = DuckDBDatastore(database="app/data/data.db")
    
    # Create LLM session for text-to-SQL conversion
    llm_session = LLMSession(
        chat_model=current_app.config.get("CHAT_MODEL", "gpt-4o-mini"),
        embedding_model=current_app.config.get("EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    
    # Create a focused prompt for SQL generation
    # The main conversation already has comprehensive schema information
    sql_generation_prompt = create_sql_generation_prompt(natural_language_query)
    
    try:
        # Try structured output first
        try:
            sql_query_response = llm_session.get_structured_output(
                messages=sql_generation_prompt,
                structured_output=SqlQuery()
            )
            sql_query = sql_query_response.query
            logger.info(f"Generated SQL query via structured output: {sql_query}")
            
            # If structured output returns empty query, fall back to chat
            if not sql_query or sql_query.strip() == "":
                logger.warning("Structured output returned empty query, falling back to regular chat")
                raise ValueError("Empty query from structured output")
                
        except Exception as struct_error:
            logger.warning(f"Structured output failed: {struct_error}, falling back to regular chat")
            
            # Fallback to regular chat if structured output fails
            chat_response = llm_session.chat(messages=sql_generation_prompt)
            content = chat_response.choices[0].message.content
            
            # Extract SQL from the response
            sql_query = extract_sql_from_response(content)
            if not sql_query:
                return f"Error: Could not extract valid SQL from response: {content}"
            
            logger.info(f"Generated SQL query via chat fallback: {sql_query}")
        
        # Execute the SQL query
        result = datastore.execute(sql_query)
        
        # Format the result as markdown (handle empty results)
        if result is None or result.empty:
            formatted_result = "No rows returned from the query."
            # Create empty dataframe for analysis
            result = pd.DataFrame()
        else:
            formatted_result = result.to_markdown(index=False, floatfmt=".2f")
        
        # Generate natural language analysis of the results
        analysis = generate_analysis(llm_session, natural_language_query, sql_query, result, formatted_result)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in text-to-SQL conversion or execution: {e}")
        return f"Error: Unable to process your query. {str(e)}"


def extract_sql_from_response(content: str) -> str:
    """Extract SQL query from LLM response content."""
    if not content:
        return ""
    
    # Look for SQL in code blocks
    sql_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return sql_match.group(1).strip()
    
    # If no code blocks, look for SELECT statements
    select_match = re.search(r'(SELECT.*?)(?:\n\n|\n$|$)', content, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()
    
    # If content looks like SQL directly, return it
    if content.strip().upper().startswith(('SELECT', 'WITH', 'SHOW')):
        return content.strip()
    
    return ""


def create_sql_generation_prompt(natural_language_query: str) -> list:
    """Create a focused prompt for SQL generation.
    
    Note: This relies on the main conversation context which already has comprehensive schema information.
    """
    
    return [
        {
            "role": "system",
            "content": """You are an expert SQL query generator. Your task is to convert natural language questions into valid SQL queries.

**CRITICAL INSTRUCTIONS:**
1. **Use ONLY the database schema information provided in the main conversation context**
2. **Generate SQL queries based strictly on the available tables and columns discussed earlier**
3. **If the requested data doesn't exist in the schema, return this exact query:**
   ```sql
   SELECT 'The requested data is not available in the current database schema' as message, 'Use available tables and columns for analysis' as suggestion
   ```

**ANTI-HALLUCINATION RULES:**
- Never use table names or columns not mentioned in the conversation
- This is a dimensional database - no financial amount columns exist
- For financial analysis, query account names with LIKE '%Revenue%' patterns
- Use text searches (LIKE) instead of numerical comparisons

**Your Role:**
- Convert the natural language question to a SQL query
- Use proper DuckDB SQL syntax
- Focus on the tables and columns that were described in the conversation
- Return clean, executable SQL

**Response Format:**
Return ONLY a valid SQL query that will execute successfully against the database schema discussed in the conversation."""
        },
        {
            "role": "user", 
            "content": f"Based on the database schema we've been discussing, convert this natural language query to SQL: {natural_language_query}"
        }
    ]


def generate_analysis(llm_session: LLMSession, original_query: str, sql_query: str, result_data, formatted_result: str) -> str:
    """Generate natural language analysis of the query results."""
    
    # Prepare the data summary for analysis
    row_count = len(result_data)
    column_info = list(result_data.columns)
    
    # Create a sample of the data for analysis (first 10 rows)
    sample_data = result_data.head(10).to_dict('records') if row_count > 0 else []
    
    analysis_prompt = [
        {
            "role": "system",
            "content": """You are a financial data analyst. Your task is to analyze query results and provide insightful natural language responses.

**CRITICAL REQUIREMENT:**
You must ALWAYS include the complete retrieved data table in your response.

**Your Role:**
- Analyze the retrieved data based on what's actually available
- Provide business insights appropriate to the data type and content
- Be honest about limitations based on the available data
- Focus on patterns, relationships, and meaningful information
- Make technical results accessible to business users

**Response Format:**
1. Start with a clear summary of findings
2. Provide business insights and analysis
3. **ALWAYS include the complete data table at the end**
4. Suggest follow-up questions when appropriate

**Example Response Structure:**
```
I found [X] records matching your query about [topic].

[Your analysis and insights here]

**Retrieved Data:**
[Include the complete formatted data table]
```"""
        },
        {
            "role": "user",
            "content": f"""Analyze these query results and provide an appropriate response.

**Original Question:** {original_query}

**SQL Query:** ```sql
{sql_query}
```

**Results:**
- Rows returned: {row_count}
- Columns: {', '.join(column_info)}
- Sample data: {sample_data}

**IMPORTANT:** You must include this complete data table in your response:
{formatted_result}

Please provide analysis AND include the complete retrieved data table."""
        }
    ]
    
    try:
        # Generate analysis using LLM
        analysis_response = llm_session.chat(messages=analysis_prompt)
        analysis_content = analysis_response.choices[0].message.content
        
        return analysis_content
        
    except Exception as e:
        logger.error(f"Error generating analysis: {e}")
        # Fallback to basic formatted output
        return f"**Query Results:**\n\nI found {row_count} records:\n\n{formatted_result}"