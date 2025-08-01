from unittest.mock import MagicMock, patch

from flask import current_app

from app.services.llm.prompts.decorator import prompt
from tests import BaseTest
from tests.utils.assertion import contains, is_equal


class TestPromptDecorator(BaseTest):
    """Test the prompt decorator functionality with various scenarios."""

    def test_prompt_decorator_with_default(self):
        """
        Test that the prompt decorator falls back to the default implementation
        when the prompt service is not configured.
        """

        @prompt()
        def test_prompt(**kwargs):
            """Default test prompt."""
            return "This is a default prompt"

        with patch.object(current_app.config, "__getitem__", return_value=None):
            result = test_prompt()

        is_equal(result, "This is a default prompt")

    def test_prompt_decorator_with_custom_name(self):
        """
        Test that the prompt decorator correctly uses a custom name
        when specified in the decorator.
        """

        @prompt(name="custom_test_prompt")
        def test_prompt(**kwargs):
            """Default test prompt."""
            return "This is a default prompt"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.return_value = "Prompt from service"
            mock_client_class.return_value = mock_client

            result = test_prompt()

            mock_client.get_prompt.assert_called_once_with(
                prompt_name="custom_test_prompt",
                fallback="This is a default prompt",
                prompt_label=None,
            )
            is_equal(result, "Prompt from service")

    def test_prompt_decorator_with_kwargs(self):
        """
        Test that the prompt decorator correctly passes kwargs to both
        the default implementation and the prompt service.
        """

        @prompt()
        def test_prompt_with_vars(**kwargs):
            """Prompt that uses variables."""
            return f"Hello, {kwargs.get('name', 'world')}!"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.side_effect = Exception("Service error")
            mock_client_class.return_value = mock_client

            result = test_prompt_with_vars(name="TextLayer")
            is_equal(result, "Hello, TextLayer!")

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()

            def mock_get_prompt(prompt_name, fallback, prompt_label=None, **kwargs):
                return f"Service: Hello, {kwargs.get('name')}!"

            mock_client.get_prompt.side_effect = mock_get_prompt
            mock_client_class.return_value = mock_client

            result = test_prompt_with_vars(name="TextLayer")
            is_equal(result, "Service: Hello, TextLayer!")

    def test_prompt_decorator_exception_handling(self):
        """
        Test that the prompt decorator handles exceptions in the prompt service
        gracefully by falling back to the default implementation.
        """

        @prompt()
        def test_prompt(**kwargs):
            """Default test prompt."""
            return "This is a default prompt"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.side_effect = Exception("Service error")
            mock_client_class.return_value = mock_client

            result = test_prompt(test_var="value")
            is_equal(result, "This is a default prompt")

    def test_prompt_decorator_local_flag(self):
        """
        Test that the local flag forces the use of the default implementation
        even when the prompt service is available.
        """

        @prompt(local=True)
        def test_prompt(**kwargs):
            """Default test prompt with local flag."""
            return "Local prompt"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.return_value = "Service prompt"
            mock_client_class.return_value = mock_client

            result = test_prompt()

            mock_client.get_prompt.assert_not_called()
            is_equal(result, "Local prompt")

    def test_prompt_decorator_with_template_variables(self):
        """
        Test that the prompt decorator correctly handles template variable substitution
        with more complex templates.
        """

        @prompt()
        def complex_template(**kwargs):
            """Complex template with multiple variables."""
            username = kwargs.get("username", "user")
            task = kwargs.get("task", "default task")
            urgency = kwargs.get("urgency", "normal")
            return f"""
            Hello {username},
            
            You need to complete the {task} task.
            This task is {urgency} priority.
            
            Regards,
            System
            """

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()

            def mock_get_prompt(prompt_name, fallback, prompt_label=None, **kwargs):
                username = kwargs.get("username", "user")
                task = kwargs.get("task", "default task")
                urgency = kwargs.get("urgency", "normal")
                return f"FROM SERVICE: Hello {username}, task {task}, urgency {urgency}"

            mock_client.get_prompt.side_effect = mock_get_prompt
            mock_client_class.return_value = mock_client

            result = complex_template(username="JohnDoe", task="coding", urgency="high")

            contains(result, "JohnDoe")
            contains(result, "coding")
            contains(result, "high")
            contains(result, "FROM SERVICE: ")

    def test_prompt_decorator_with_chat_messages(self):
        """
        Test that the prompt decorator works with structured chat message formats
        that return a list of message dictionaries instead of a single string.
        """

        @prompt()
        def chat_messages(**kwargs):
            """Return a list of chat messages."""
            system_message = kwargs.get("system", "You are a helpful assistant.")
            user_message = kwargs.get("user_query", "Hello")

            return [{"role": "system", "content": system_message}, {"role": "user", "content": user_message}]

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.side_effect = Exception("Service unavailable")
            mock_client_class.return_value = mock_client

            result = chat_messages(system="You are a coding assistant.", user_query="Help with Python")

            is_equal(len(result), 2)
            is_equal(result[0]["role"], "system")
            is_equal(result[0]["content"], "You are a coding assistant.")
            is_equal(result[1]["role"], "user")
            is_equal(result[1]["content"], "Help with Python")

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.return_value = [
                {"role": "system", "content": "SERVICE: You are a coding assistant."},
                {"role": "user", "content": "SERVICE: Help with Python"},
            ]
            mock_client_class.return_value = mock_client

            result = chat_messages(system="You are a coding assistant.", user_query="Help with Python")

            is_equal(len(result), 2)
            is_equal(result[0]["role"], "system")
            is_equal(result[0]["content"], "SERVICE: You are a coding assistant.")
            is_equal(result[1]["role"], "user")
            is_equal(result[1]["content"], "SERVICE: Help with Python")

    def test_prompt_decorator_with_prompt_label(self):
        """
        Test that the prompt decorator correctly uses the prompt_label parameter
        when specified.
        """

        @prompt(prompt_label="test_label")
        def labeled_prompt(**kwargs):
            """Prompt with a specified label."""
            return "Default labeled prompt"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_prompt.return_value = "Prompt with label from service"
            mock_client_class.return_value = mock_client

            result = labeled_prompt()

            mock_client.get_prompt.assert_called_once_with(
                prompt_name="labeled_prompt", fallback="Default labeled prompt", prompt_label="test_label"
            )
            is_equal(result, "Prompt with label from service")

    def test_prompt_decorator_with_config_prompt_label(self):
        """
        Test that the prompt decorator correctly uses the PROMPT_LABEL from config
        when no explicit prompt_label is specified.
        """

        @prompt()
        def config_labeled_prompt(**kwargs):
            """Prompt using label from config."""
            return "Default config labeled prompt"

        with patch.object(current_app.config, "get") as mock_config_get:
            mock_config_get.return_value = "config_label"

            with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.get_prompt.return_value = "Prompt with config label"
                mock_client_class.return_value = mock_client

                result = config_labeled_prompt()

                mock_client.get_prompt.assert_called_once_with(
                    prompt_name="config_labeled_prompt",
                    fallback="Default config labeled prompt",
                    prompt_label="config_label",
                )
                is_equal(result, "Prompt with config label")

    def test_prompt_decorator_with_null_prompt_service(self):
        """
        Test that the prompt decorator falls back to default implementation
        when prompt service returns None.
        """

        @prompt()
        def test_prompt_with_null_service(**kwargs):
            """Default prompt for null service test."""
            return "Default when service is None"

        with patch("app.services.llm.prompts.decorator.PromptClient") as mock_client_class:
            mock_client_class.return_value = None

            result = test_prompt_with_null_service()
            is_equal(result, "Default when service is None")
