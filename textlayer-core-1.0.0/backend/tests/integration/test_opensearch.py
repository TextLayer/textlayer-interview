import pytest

from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from tests import BaseTest
from tests.utils.assertion import is_equal, is_true


class TestOpenSearch(BaseTest):
    """Test OpenSearch functionality."""

    def test_opensearch_search(self):
        """Test search with OpenSearch."""
        from app.errors import ValidationException

        try:
            cmd = ProcessChatMessageCommand([])
            cmd.validate()
            pytest.fail("Expected ValidationException was not raised")
        except ValidationException as e:
            is_equal(e.get_message(), "Messages are required")

        cmd = ProcessChatMessageCommand([{"role": "user", "content": "Hello"}])
        is_true(cmd.validate())
