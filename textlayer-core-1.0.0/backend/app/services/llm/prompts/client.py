from typing import Dict, Optional, Type

from flask import current_app

from app import logger
from app.services.llm.prompts.providers.base import BasePromptService, PromptContent
from app.services.llm.prompts.providers.langfuse import LangfusePromptService


class PromptClient:
    """Client for accessing prompts through configurable providers."""

    # Available prompt providers registry
    _providers: Dict[str, Type[BasePromptService]] = {
        "langfuse": LangfusePromptService,
    }

    def __init__(self) -> None:
        """Initialize the prompt provider based on application configuration."""
        self.prompt_service = self._get_provider()

    def _get_provider(self) -> Optional[BasePromptService]:
        """
        Find and initialize the appropriate prompt provider.

        Returns:
            Initialized provider instance or None if unavailable
        """
        provider_name = current_app.config.get("PROMPT_PROVIDER", "").lower()

        # Handle missing configuration
        if not provider_name:
            logger.warning("PROMPT_PROVIDER not configured")
            return None

        # Handle unknown provider
        if provider_name not in self._providers:
            logger.warning(f"Unknown provider '{provider_name}'. Available: {', '.join(self._providers.keys())}")
            return None

        # Try to initialize provider
        try:
            provider = self._providers[provider_name]()

            # Check if provider is properly configured
            if not provider.is_available():
                logger.warning(f"Provider '{provider_name}' not properly configured")
                return None

            return provider

        except Exception as e:
            logger.error(f"Failed to initialize '{provider_name}': {e}")
            return None

    def get_prompt(
        self, prompt_name: str, fallback: Optional[PromptContent] = None, prompt_label: Optional[str] = None, **kwargs
    ) -> PromptContent:
        """
        Get a prompt with fallback to default implementation.

        Args:
            prompt_name: The prompt identifier
            fallback: Default prompt to use if provider fails
            prompt_label: Optional label to filter prompts
            **kwargs: Variables for prompt template

        Returns:
            The compiled prompt content (from provider or fallback)
        """
        # Return fallback if no provider is available
        if self.prompt_service is None:
            return fallback or [{"role": "system", "content": f"No provider for '{prompt_name}'"}]

        # Try to get prompt from provider
        try:
            return self.prompt_service.get_prompt(prompt_name, fallback=fallback, prompt_label=prompt_label, **kwargs)
        except Exception as e:
            logger.error(f"Error fetching '{prompt_name}': {e}")
            return fallback or [{"role": "system", "content": f"Error fetching '{prompt_name}'"}]
