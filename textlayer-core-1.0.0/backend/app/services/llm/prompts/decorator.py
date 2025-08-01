from functools import wraps
from typing import Any, Callable, Optional

from flask import current_app

from app import logger
from app.services.llm.prompts.client import PromptClient
from app.services.llm.prompts.providers.base import PromptContent

# Type for prompt generating functions
PromptFunc = Callable[..., PromptContent]


def prompt(
    name: Optional[str] = None, local: bool = False, prompt_label: Optional[str] = None
) -> Callable[[PromptFunc], PromptFunc]:
    """
    Decorator that enables dynamic prompt loading with local fallback.

    If the provider fails or isn't available, uses the decorated function's
    implementation as a fallback prompt.

    Args:
        name: Optional prompt name (defaults to function name)
        local: If True, forces the use of the local prompt implementation
               instead of fetching from the prompt service.

    Example:
        @prompt("system_instructions")
        def system_prompt(**kwargs) -> list[dict]:
            return [{"role": "system", "content": "You are a helpful assistant."}]

        @prompt(local=True)  # Forces local prompt usage
        def system_message(**kwargs):
            return "default prompt text ..."

        @prompt(prompt_label="production") # Forces to use a specific prompt label
        def system_message(**kwargs):
            return "default prompt text ..."
    Returns:
        A decorator that wraps the prompt-generating function.
        The wrapped function will first attempt to fetch the prompt from
        the configured provider, falling back to the local implementation
        if necessary.
    """

    def decorator(func: PromptFunc) -> PromptFunc:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> PromptContent:
            # Use function name if no explicit name provided
            prompt_name = name or func.__name__

            # Get default implementation from decorated function
            default_prompt = func(*args, **kwargs)

            if local:
                # If local is True, return the default prompt directly
                return default_prompt

            _prompt_label = prompt_label or current_app.config.get("PROMPT_LABEL", None)

            try:
                # Try to get prompt from configured provider
                return PromptClient().get_prompt(
                    prompt_name=prompt_name, fallback=default_prompt, prompt_label=_prompt_label, **kwargs
                )
            except Exception as e:
                logger.warning(f"Prompt '{prompt_name}' error: {e}")
                return default_prompt

        return wrapper  # type: ignore

    return decorator
