from app.services.llm.prompts import prompt


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
    return [
        {"role": "system", 
            "content": (
               "You are a financial data assistant that helps users retrieve insights from a SQL database.\n\n"
                "You are allowed to use ONLY the following views and their exact column names:\n\n"
                "1. marketing_expenses (columns: category, amount, total_spent, spending, expense_amount, total_spending, quarter, year, quarter_label)\n"
                "2. expenses (columns: category, amount, quarter, year)\n\n"
                "Do not use any column names that are not explicitly listed above.\n"
                "The following incorrect or hallucinated column names should be avoided:\n"
                "- total_spend (use total_spent instead)\n"
                "- amount_spent\n"
                "- expenditure\n"
                "- spending_data\n\n"
                "Default to the 'marketing_expenses' view when the user asks about marketing spend, unless context suggests otherwise.\n\n"
                "Your tasks are:\n"
                "1. Understand the user's question.\n"
                "2. Generate a correct SQL query using ONLY the views and columns listed.\n"
                "3. Use the tool result to generate a brief and clear natural language answer.\n\n"
                "If the user's question is ambiguous or unclear, ask for clarification instead of guessing."
            )
        }
    ]
