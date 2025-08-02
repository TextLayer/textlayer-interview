from functools import cached_property
from typing import Optional, TypeVar

from flask import current_app

from app import logger
from app.services.llm.prompts.providers.base import BasePromptService, PromptContent

# Type for Langfuse prompt objects
LangfusePrompt = TypeVar("LangfusePrompt")


class LangfusePromptService(BasePromptService):
    """Service for fetching and compiling prompts from Langfuse."""

    def __init__(self) -> None:
        """Initialize the Langfuse prompt service."""
        self._client = None

    @cached_property
    def langfuse(self):
        """Lazily initialize and cache the Langfuse client."""
        try:
            from langfuse import Langfuse

            return Langfuse()
        except ImportError as e:
            logger.warning(f"Langfuse SDK not installed: {e}")
            return None

    def is_available(self) -> bool:
        """
        Check if Langfuse is properly configured and available.

        Returns:
            True if Langfuse is available and configured
        """
        config = current_app.config
        return all(
            [
                config.get("LANGFUSE_PUBLIC_KEY"),
                config.get("LANGFUSE_SECRET_KEY"),
                config.get("LANGFUSE_HOST"),
                self.langfuse is not None,
            ]
        )

    def get_prompt(
        self, prompt_name: str, fallback: Optional[PromptContent] = None, prompt_label: Optional[str] = None, **kwargs
    ) -> PromptContent:
        """
        Fetch and compile a prompt from Langfuse.

        Args:
            prompt_name: Name of the prompt in Langfuse
            fallback: Default prompt to use if not found
            prompt_label: Optional label to filter prompts
            **kwargs: Variables for template substitution

        Returns:
            The compiled prompt content
        """
        # Return fallback if Langfuse isn't available
        if not self.is_available():
            if fallback is not None:
                return fallback
            raise RuntimeError("Langfuse service unavailable")

        try:
            # Get and compile the prompt
            lf_prompt = self.langfuse.get_prompt(prompt_name, type="chat", label=prompt_label)
            compiled = lf_prompt.compile(**kwargs, fallback=fallback)

            # Handle string prompts by wrapping them as system messages
            if isinstance(compiled, str):
                return [{"role": "system", "content": compiled}]

            return compiled

        except Exception as e:
            self._log_error(f"get_prompt({prompt_name})", e)
            if fallback is not None:
                return fallback
            raise
