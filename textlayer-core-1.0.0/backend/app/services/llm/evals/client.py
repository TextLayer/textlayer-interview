from typing import Any, Dict, List, Optional, Type

from flask import current_app

from app.services.llm.evals.providers.base import BaseEvalService
from app.services.llm.evals.providers.langfuse import LangfuseEvalService


class EvalClient:
    """Client for accessing evaluation services through configurable providers."""

    # Available evaluation providers registry
    _providers: Dict[str, Type[BaseEvalService]] = {
        "langfuse": LangfuseEvalService,
        # Add more providers here as they become available
    }

    def __init__(self) -> None:
        """Initialize the appropriate evaluation provider based on configuration."""
        self.eval_service = self._get_provider()

    def _get_provider(self) -> BaseEvalService:
        """
        Find and initialize the appropriate evaluation provider.

        Returns:
            Initialized provider instance

        Raises:
            ValueError: If no valid provider is configured
        """
        provider_name = current_app.config.get("EVAL_PROVIDER", "").lower()

        # Handle missing configuration
        if not provider_name:
            raise ValueError("EVAL_PROVIDER not configured")

        # Handle unknown provider
        if provider_name not in self._providers:
            raise ValueError(f"Unknown provider '{provider_name}'. Available: {', '.join(self._providers.keys())}")

        # Initialize provider
        return self._providers[provider_name]()

    def get_datasets(self, dataset_names: Optional[List[str]] = None) -> List[Any]:
        """
        Get datasets from the configured provider, with optional filtering.

        Args:
            dataset_names: Optional list of dataset names to filter by

        Returns:
            List of dataset objects
        """
        return self.eval_service.get_datasets(dataset_names)

    def get_dataset_items(self, dataset_name: str) -> List[Any]:
        """
        Get items from a specified dataset.

        Args:
            dataset_name: Name of the dataset to fetch items from

        Returns:
            List of dataset items
        """
        return self.eval_service.get_dataset_items(dataset_name)

    def setup_evaluation_context(self, item: Any) -> None:
        """
        Set up evaluation context for an item.

        Args:
            item: The evaluation item to set up context for
        """
        return self.eval_service.setup_evaluation_context(item)

    def get_observation_context(self, item: Any, run_name: str) -> Any:
        """
        Get observation context for tracking item evaluation.

        Args:
            item: The evaluation item to observe
            run_name: Name for the evaluation run

        Returns:
            A context manager for the observation
        """
        return self.eval_service.get_observation_context(item, run_name)
