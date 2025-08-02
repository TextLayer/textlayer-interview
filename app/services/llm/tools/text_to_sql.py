from langfuse.decorators import observe
from vaul import tool_call
from app import logger
from app.services.llm.workflows.text_to_sql_workflow import run_sql_workflow_sync


@tool_call
@observe
def text_to_sql(user_query: str) -> str:
    """A tool for processing natural language queries that require SQL database for answer generation
    
    Args:
        - user_query: The natural language query sent by the user
    
    Returns:
        - a JSON containing user_query, SQL Query generated, SQL Query Results 
    """

    return run_sql_workflow_sync(user_query=user_query)