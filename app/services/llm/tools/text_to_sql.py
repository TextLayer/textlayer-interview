from vaul import tool_call

@tool_call
def text_to_sql(messages):
    sql = "SELECT revenue FROM sales WHERE quarter = 'Q2'"
    result = [{"revenue": 75000}]
    return {
        "sql": sql,
        "result": result
    }

text_to_sql_tool = text_to_sql
