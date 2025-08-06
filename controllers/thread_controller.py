from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from app.commands.threads.process_chat_message_agentic import ProcessChatMessageAgenticCommand

from app.controllers.controller import Controller


class ThreadController(Controller):
    """
    A controller for threads.
    """
    def process_chat_message(self, chat_messages: list) -> list:
        return self.executor.execute_write(ProcessChatMessageCommand(chat_messages))

    def process_chat_message_agentic(self, chat_messages: list) -> list:
        """
        Process chat message using LangGraph multi-agent system
        """
        return self.executor.execute_write(ProcessChatMessageAgenticCommand(chat_messages))
