from unittest.mock import patch

import pytest

from app.commands.threads.process_chat_message import ProcessChatMessageCommand
from app.controllers.thread_controller import ThreadController
from tests import BaseTest
from tests.utils.assertion import is_equal, is_true


class TestThreadProcessing(BaseTest):
    """Test thread processing functionality."""

    def test_process_chat_message_command_validation(self):
        """Test validation in ProcessChatMessageCommand."""
        from app.errors import ValidationException

        try:
            cmd = ProcessChatMessageCommand([])
            cmd.validate()
            pytest.fail("Expected ValidationException was not raised")
        except ValidationException as e:
            is_equal(e.get_message(), "Messages are required")

        cmd = ProcessChatMessageCommand([{"role": "user", "content": "Hello"}])
        is_true(cmd.validate())

    def test_thread_controller_process_chat_message(self):
        """Test ThreadController.process_chat_message method."""
        controller = ThreadController()

        messages = [{"role": "user", "content": "Say hello!"}]

        expected_result = messages + [
            {
                "role": "assistant",
                "content": "Hello! I'm here to help.",
                "finish_reason": "stop",
            }
        ]

        with patch.object(controller.executor, "execute_write", return_value=expected_result):
            result = controller.process_chat_message(messages)

        is_equal(result, expected_result)
