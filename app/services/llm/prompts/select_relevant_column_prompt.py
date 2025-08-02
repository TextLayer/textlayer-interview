from app.services.llm.prompts import prompt


@prompt()
def select_relevant_column_prompt(**kwargs) -> str:
    """
    This prompt is used to select relevant columns from a table schema based on the user question.
    """
    # Extract the required parameters from kwargs
    table_context = kwargs.get('table_context', '')
    query_str = kwargs.get('query_str', '')
    
    return f"""
You are given a user question and a set of table schemas from a SQL database. You are tasked to return the name of the columns that are the most related to the user question.
Use **only** the information in the schemas provided. Be careful not to introduce columns that don't exist in the table.

These are information for user query, table schema information:
Question: {query_str}
Tables information:
{table_context}

Guidelines to generate the output:
- Please carefully review the user question and the table schema :
- Select the columns that are the most related to the user question based on the column names and overall table schema.
- You don't have to use all the tables and all the columns. Pick the ones that are the most related and can possibly contain information that answers user's question.
- Generating Output
    - Make sure the output is in JSON format with no leading or trailing characters before and after the closing and opening JSON curly brackets.
    - Make sure you use the name of the table as key in json and the columns as list of values.
    - when you decided to use a column or columns from a table or multiple tables, please make sure the name of the Tables and Columns are used exactly as shown in the schema above. Don't change the letters from upper case to lowercase or vice versa. Don't add symbols or remove symbols from the name. USe them as is in your JSON output.
    - Make sure the names of the tables and columns are in double quotes to be processed later as strings.

Use the following JSON output as en example to generate your own output. The following is just an example to show that tables names should be the key and column name(s) should be the value (a list of strings) in the JSON output.
{{
"table 2": ["column 1", "column 5"],
"table 5": ["column 2", "column 3"],
.
.
.
}}
"""