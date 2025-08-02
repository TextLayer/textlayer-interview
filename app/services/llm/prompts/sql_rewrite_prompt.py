from app.services.llm.prompts import prompt


@prompt()
def sql_rewrite_prompt(**kwargs) -> str:
    """
    This prompt is used to refine a SQL query that was previously generated to 
    answer a user query. Related tables to the user query are identified and a Context is generated.
    The aformentioned Context will be dynamically injected into this prompt to 
    provide the LLM with the knowledge to generate an efficient and relevant SQL query. 
    """
    # Extract the required parameters from kwargs
    dialect = kwargs.get('dialect', '')
    table_context = kwargs.get('table_context', '')
    query_str = kwargs.get('query_str', '')
    sql_query = kwargs.get('sql_query', '')
    
    return f"""
You are given a user question, a SQL query that was previously generated to answer it, and a schema description showing available tables and columns.

Please carefully review the SQL query in light of:
- The user question: does it answer the question fully and correctly?
- The schema: does it reference only existing tables and columns, and qualify columns correctly where needed?
- Relevance: does it select only relevant columns (not all columns), and use appropriate filters or joins?

If the SQL query is correct and optimal, return it as-is. If it is incorrect or suboptimal, refine it to better meet the user's intent. Make sure to create a syntactically correct {dialect} query to run (use double quotes instead of backsticks for identifiers).

Use **only** the information in the schema provided. Be careful not to introduce columns or tables that don't exist.

These are information for user query, previously generated SQL query and table information:
Question: {query_str}
previously generated SQL query: {sql_query}
Tables information:
{table_context}

Guidelines to generate the output:
- You are requried to generate an output in the JSON format shown below with no leading or trailing characters outside the JSON's opening and closing curley brackets.
- Review the input question, previously generated SQL query and the table information and decide if the SQL query need improvement or not.
{{
"query": "Place your final SQL query to run here in quotes"
}}
"""