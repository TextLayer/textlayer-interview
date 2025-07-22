from app.controllers.controller import Controller
from app.services.api.client import TextLayerAPIClient


class ThreadController(Controller):
    """
    A controller for threads that supports both local and remote processing.
    """
    def __init__(self):
        super().__init__()
        self.api_client = TextLayerAPIClient()

    def process_chat_message(self, chat_messages: list) -> list:
        """Process chat message using hybrid local/remote approach"""
        return self.api_client.process_chat_message(chat_messages)

    def process_chat_message_stream(self, chat_messages: list):
        """Stream chat message processing using hybrid local/remote approach"""
        return self.api_client.process_chat_message_stream(chat_messages)

    def get_api_status(self) -> dict:
        """Get current API configuration and status"""
        return self.api_client.get_api_status()
