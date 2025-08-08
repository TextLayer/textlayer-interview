from langchain_core.tools import tool
from typing import Dict, Any
import json

from app.services.llm.tools.text_to_sql import text_to_sql as vaul_text_to_sql


@tool
def text_to_sql_langchain(natural_language_query: str) -> str:
    """
    Convert natural language queries about financial data into SQL queries and execute them.
    
    Args:
        natural_language_query: The user's question in plain English about financial data
        
    Returns:
        JSON string containing the SQL query, results, and summary
    """
    try:
        # Use the existing Vaul tool implementation
        from app import logger
        logger.debug(f"text_to_sql_langchain called with query: {natural_language_query}")
        
        result = vaul_text_to_sql(natural_language_query)
        
        logger.debug(f"text_to_sql result: {result}")
        return json.dumps(result)
    except Exception as e:
        from app import logger
        logger.error(f"Error in text_to_sql_langchain: {str(e)}")
        return json.dumps({
            "error": f"Failed to process query: {str(e)}",
            "query": natural_language_query
        })
