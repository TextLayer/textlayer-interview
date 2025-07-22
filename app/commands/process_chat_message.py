from app import logger
from app.services.llm.session import LLMSession
from app.services.sql.sql_executor import SQLExecutor


class ProcessChatMessage:
    def __init__(self, messages, **kwargs):
        """Initialize the process chat message command."""
        self.chat_kwargs = {
            'messages': messages,
            **kwargs
        }

    def execute(self):
        """Execute the process chat message command."""
        try:
            response = LLMSession().chat(**self.chat_kwargs)

            # Extract and execute SQL from the response using enhanced executor
            sql_executor = SQLExecutor()
            enhanced_response = sql_executor.extract_and_execute_sql(
                response['content']
            )

            # Update the response content with SQL results and download links
            response['content'] = enhanced_response

            return response

        except Exception as e:
            logger.error(f"Failed to fetch chat response: {e}")
            logger.error(f"Chat kwargs: {self.chat_kwargs}")
            raise Exception(f"Error in fetching chat response: {e}")