from app.services.llm.prompts import prompt


@prompt()
def text_to_sql_prompt(**kwargs) -> str:
    """
    This prompt is used to generate a SQL query from a user question/query.
    Related tables to the user query are identified and a Context is generated.
    The aformentioned Context will be dynamically injected into this prompt to 
    provide the LLM with the knowledge to generate an efficient and relevant SQL query. 
    """
    # Extract the required parameters from kwargs
    dialect = kwargs.get('dialect', '')
    table_context = kwargs.get('table_context', '')
    query_str = kwargs.get('query_str', '')
    
    return f"""
Given an input question, create a syntactically correct {dialect} query to run (use double quotes instead of backsticks for identifiers).

Never query for all the columns from a specific table, only ask for a few relevant columns given the question.

Pay attention to use only the table and column names that you can see in the schema description below. Be careful to not query for columns that do not exist. Pay attention to which column is in which table. Also, qualify column names with the table name when needed.

Only use tables information listed below.
{table_context}

Question: {query_str}

Guidelines to generate the output:
- You are requried to generate an output in the JSON format shown below with no leading or trailing characters outside the JSON's opening and closing curley brackets.
- Review the input question and compare it with the tables information shared above.
{{
"query": "Place the generated SQL query to run here in quotes"
}}
"""