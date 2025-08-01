from unittest.mock import MagicMock, patch

from flask import current_app

from app.services.llm.prompts.providers.langfuse import LangfusePromptService
from tests import BaseTest
from tests.utils.assertion import is_equal, is_false, is_true


class TestPromptProvider(BaseTest):
    """Test the prompt provider implementations."""

    def test_langfuse_provider_is_available(self):
        """Test that LangfusePromptService checks configuration correctly."""
        provider = LangfusePromptService()

        with patch.object(current_app.config, "get", return_value="test_value"):
            with patch.object(provider, "langfuse", MagicMock()):
                is_true(provider.is_available())

        with patch.object(current_app.config, "get", return_value=None):
            is_false(provider.is_available())

    def test_langfuse_provider_get_prompt(self):
        """Test that LangfusePromptService gets and compiles prompts correctly."""
        provider = LangfusePromptService()

        mock_prompt = MagicMock()
        mock_prompt.compile.return_value = "Compiled prompt"

        mock_langfuse_instance = MagicMock()
        mock_langfuse_instance.get_prompt.return_value = mock_prompt

        with patch.object(provider, "langfuse", mock_langfuse_instance):
            with patch.object(provider, "is_available", return_value=True):
                result = provider.get_prompt("test_prompt", test_var="value")

                is_equal(len(result), 1)
                is_equal(result[0]["role"], "system")
                is_equal(result[0]["content"], "Compiled prompt")

                mock_prompt.compile.return_value = [{"role": "system", "content": "Test"}]
                result = provider.get_prompt("test_prompt", test_var="value")
                is_equal(len(result), 1)
                is_equal(result[0]["role"], "system")
                is_equal(result[0]["content"], "Test")

                mock_langfuse_instance.get_prompt.side_effect = Exception("Test error")
                fallback_value = "Fallback prompt"
                result = provider.get_prompt("test_prompt", fallback=fallback_value)
                is_equal(result, fallback_value)
