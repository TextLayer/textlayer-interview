from app.services.llm.prompts import prompt

@prompt()
def llm_judge_prompt(user_question: str, sql: str, summary: str) -> str:
    """
    Prompt for LLM-as-a-Judge to verify and improve a summary based on the SQL result and the user's original question.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are an assistant that helps verify the accuracy of SQL-generated summaries.\n\n"
                "Your job is to carefully review a natural language summary and improve it if needed, based on:\n"
                "- The original user question\n"
                "- The actual SQL result\n\n"
                "Instructions:\n"
                "1. Make sure the summary directly answers the user's question.\n"
                "2. Ensure the information matches what the SQL query retrieves.\n"
                "3. If the summary is incomplete, misleading, or unclear, rewrite it to be accurate and concise.\n\n"
                "Only return the revised summary. Do not include any SQL, explanations, or commentary."
            )
        },
        {
            "role": "user",
            "content": (
                f"User question:\n{user_question}\n\n"
                f"SQL result:\n{sql}\n\n"
                f"Generated summary:\n{summary}\n\n"
                "Please revise and return a better version if needed:"
            )
        }
    ]
