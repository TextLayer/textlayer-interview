from unittest.mock import patch

from app.services.llm.client.chat import ChatClient
from tests import BaseTest
from tests.utils.assertion import is_equal, is_not_none


class TestLLMSession(BaseTest):
    """Test the LLM session functionality."""

    def test_llm_session_initialization(self):
        """Test LLMSession initialization."""
        client = ChatClient()

        is_not_none(client)

    def test_llm_session_trim_message_history(self):
        """Test passing messages to the ChatClient."""
        client = ChatClient()

        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
        ]

        with patch.object(client, "chat", return_value=messages):
            result = client.chat(messages=messages)
            is_equal(result, messages)
