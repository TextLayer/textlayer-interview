from app.services.llm.prompts import prompt
import os
from pathlib import Path


@prompt()
def chat_prompt(**kwargs) -> str:
    """
    This prompt is used to chat with the LLM.

    You can use the kwargs to pass in data that will be used to generate the prompt.
    
    For example, if you want to pass in a list of messages, you can do the following:
    ```python
    chat_prompt(example_variable="test")
    ```

    You can then use the example_variable in the prompt like this:
    ```
    return [
        {"role": "system", "content": "Your name is %(name)s."} % kwargs
    ]
    ```
    """
    
    # Load database schema context
    schema_context = ""
    try:
        # Try multiple possible paths
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "scripts" / "database_schema_prompt.txt",
            Path.cwd() / "scripts" / "database_schema_prompt.txt",
            Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "database_schema_prompt.txt"
        ]
        
        schema_path = None
        for path in possible_paths:
            if path.exists():
                schema_path = path
                break
        
        if schema_path:
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_content = f.read()
                schema_context = f"""

<DATABASE_SCHEMA_CONTEXT>
{schema_content}
</DATABASE_SCHEMA_CONTEXT>

This database schema context provides detailed information about the financial database structure, including tables, columns, sample data, and relationships. Use this information when generating SQL queries or answering questions about the data.
"""
        else:
            schema_context = f"\n\n<ERROR: Database schema file not found. Searched paths: {[str(p) for p in possible_paths]}>"
    except Exception as e:
        schema_context = f"\n\n<ERROR: Could not load database schema context: {e}>"
    
    system_content = f"""You are a helpful AI assistant specializing in financial data analysis and SQL query generation. 

You have access to a financial business intelligence database with the following capabilities:
- Generate SQL queries for data analysis
- Answer questions about financial data
- Explain database structure and relationships
- Provide insights based on available data

When users ask questions about data (like "who is our top customer"), you should:
1. Analyze what information they're looking for
2. Use the text_to_sql tool to generate appropriate SQL queries
3. Interpret and explain the results in business terms

Key Guidelines:
- Always use the provided database schema context when generating SQL queries
- Be specific about which tables and columns you're using
- Explain your reasoning for the SQL query structure
- Provide business-friendly interpretations of technical results
- If data is insufficient to answer a question, explain what additional information would be needed{schema_context}"""

    return [
        {"role": "system", "content": system_content},
    ]
