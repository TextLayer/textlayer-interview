from contextlib import nullcontext
from functools import cached_property
from typing import Any, List, Optional

from app import logger
from app.services.llm.evals.providers.base import BaseEvalService


class LangfuseEvalService(BaseEvalService):
    """Service for evaluating LLMs via Langfuse."""

    def __init__(self) -> None:
        """Initialize the Langfuse evaluation service."""
        self._langfuse = None

    @cached_property
    def langfuse(self):
        """Lazily initialize and cache Langfuse client."""
        try:
            from langfuse import Langfuse

            return Langfuse()
        except ImportError as e:
            raise ImportError(f"Langfuse package is not installed: {e}") from e

    def _safe_call(self, func, default: Any) -> Any:
        """
        Helper to invoke Langfuse operations with error logging and default fallback.
        """
        try:
            return func()
        except Exception as e:
            logger.error("Langfuse error in %s: %s", func.__name__, e)
            return default

    def get_datasets(self, dataset_names: Optional[List[str]] = None) -> List[Any]:
        """
        Fetch datasets from Langfuse with optional filtering.

        Args:
            dataset_names: Optional list of dataset names to filter by

        Returns:
            List of matching dataset objects
        """
        # Get all datasets from Langfuse
        datasets = self._safe_call(
            lambda: self.langfuse.api.datasets.list().data,
            [],
        )

        # Filter by name if specified
        if dataset_names:
            return [d for d in datasets if d.name in dataset_names]
        return datasets

    def get_dataset_items(self, dataset_name: str) -> List[Any]:
        """
        Retrieve active items for a specified dataset.

        Args:
            dataset_name: Name of dataset to retrieve items from

        Returns:
            List of active dataset items
        """
        from langfuse.client import DatasetStatus

        # Get active items only
        return self._safe_call(
            lambda: [
                item
                for item in self.langfuse.get_dataset(name=dataset_name).items
                if item.status == DatasetStatus.ACTIVE
            ],
            [],
        )

    def setup_evaluation_context(self, item: Any) -> None:
        """
        Update Langfuse trace context with evaluation item metadata.

        Args:
            item: Evaluation item to extract metadata from
        """
        from langfuse.decorators import langfuse_context

        def _update():
            metadata = {
                "input": item.input,
                "expected_output": item.expected_output,
            }

            # Safely handle metadata which might be None
            if hasattr(item, "metadata") and item.metadata is not None:
                metadata.update(item.metadata)

            langfuse_context.update_current_trace(metadata=metadata)

        self._safe_call(_update, None)

    def get_observation_context(self, item: Any, run_name: str) -> Any:
        """
        Get a Langfuse observation context for the item.

        Args:
            item: Evaluation item to observe
            run_name: Name for the observation

        Returns:
            Langfuse observation context or no-op context
        """
        return self._safe_call(lambda: item.observe(run_name=run_name), nullcontext())
