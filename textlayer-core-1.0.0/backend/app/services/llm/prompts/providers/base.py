from abc import ABC, abstractmethod
from typing import Dict, List, Optional, TypeVar, Union

# Type for prompt content
PromptContent = Union[str, List[Dict[str, str]]]

# Type variable for prompt objects from providers
T_Prompt = TypeVar("T_Prompt")


class BasePromptService(ABC):
    """
    Abstract base class for prompt services.

    All prompt providers must implement:
    - is_available(): Check if the provider is configured
    - get_prompt(): Fetch and compile a prompt
    """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and configured.

        Returns:
            True if available, False otherwise
        """
        pass

    @abstractmethod
    def get_prompt(
        self, prompt_name: str, fallback: Optional[PromptContent] = None, prompt_label: Optional[str] = None, **kwargs
    ) -> PromptContent:
        """
        Fetch and compile a prompt by name.

        Args:
            prompt_name: The prompt identifier
            fallback: Default prompt if the requested one is not found
            prompt_label: Optional label to filter prompts
            **kwargs: Variables for template substitution

        Returns:
            The compiled prompt content
        """
        pass

    def _log_error(self, operation: str, error: Exception) -> None:
        """Log errors with consistent formatting."""
        logger = __import__("logging").getLogger(__name__)
        logger.error("PromptService error in %s: %s", operation, error)
