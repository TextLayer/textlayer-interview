from app.commands.threads.process_chat_message import ProcessChatMessageCommand

from app.controllers.controller import Controller


class ThreadController(Controller):
    """
    A controller for threads.
    """
    def process_chat_message(self, chat_messages: list) -> list:
        return self.executor.execute_write(ProcessChatMessageCommand(chat_messages))
    
    def process_chat_message_stream(self, chat_messages: list) -> list:
        """
        Process chat message for streaming response.
        Uses the same enhanced processing but optimized for streaming.
        """
        # Use the same enhanced command - all improvements are included
        return self.executor.execute_write(ProcessChatMessageCommand(chat_messages))
