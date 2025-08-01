from app.services.llm.prompts import prompt
from app.services.llm.prompts.schema_helper import get_database_schema

def chat_prompt(**kwargs) -> str:
    # Get the complete schema with sample data
    schema = get_database_schema()
    
    return [
        {"role": "system", "content": f"""{schema}

IMPORTANT SQL RULES:
- Use ONLY the exact table and column names from the schema above
- Write proper SQL SELECT statements only
- Column names with spaces need double quotes: "Product Line", "Channel Parent", "Customer Since", "Sales Manager"
- String values use single quotes: WHERE Name = 'Gross Revenue'

EXAMPLES based on your schema:
- Show accounts: SELECT Name FROM account
- Account hierarchy: SELECT a1.Name as Parent, a2.Name as Child FROM account a1 JOIN account a2 ON a1.Key = a2.ParentId WHERE a1.Name = 'Gross Revenue'
- Customers by region: SELECT Name FROM customer WHERE ParentId = 'C0000'
- Time periods: SELECT Name, Year, Quarter FROM time WHERE Year = '2018'

Write valid SQL SELECT statements using the exact schema above!"""}
    ]