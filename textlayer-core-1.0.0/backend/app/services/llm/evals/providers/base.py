from abc import ABC, abstractmethod
from contextlib import nullcontext
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, TypeVar

# Type variables for generic implementation
T_Dataset = TypeVar("T_Dataset")
T_Item = TypeVar("T_Item", bound="EvalItem")


class EvalItem(Protocol):
    """Protocol defining the required interface for evaluation items."""

    @property
    def input(self) -> Any:
        """The input to evaluate."""
        ...

    @property
    def expected_output(self) -> Any:
        """The expected output for comparison."""
        ...

    @property
    def metadata(self) -> Dict[str, Any]:
        """Additional metadata for the evaluation item."""
        ...

    def observe(self, run_name: str) -> Any:
        """Get a context manager for observing this item's evaluation."""
        ...


class BaseEvalService(Generic[T_Dataset, T_Item], ABC):
    """
    Abstract base for evaluation services.

    All evaluation providers must implement:
    - get_datasets(): Retrieve available datasets
    - get_dataset_items(): Get items from a specific dataset
    """

    def _safe_call(self, func: Callable[[], Any], default: Any) -> Any:
        """Execute function with error handling and default fallback."""
        try:
            return func()
        except Exception as e:
            self._log_error(func.__name__, e)
            return default

    def _log_error(self, operation: str, error: Exception) -> None:
        """Log errors with consistent formatting."""
        logger = __import__("logging").getLogger(__name__)
        logger.error("EvalService error in %s: %s", operation, error)

    @abstractmethod
    def get_datasets(self, dataset_names: Optional[List[str]] = None) -> List[T_Dataset]:
        """
        Retrieve available datasets with optional filtering.

        Args:
            dataset_names: Optional list of dataset names to filter by

        Returns:
            List of matching datasets
        """
        pass

    @abstractmethod
    def get_dataset_items(self, dataset_name: str) -> List[T_Item]:
        """
        Retrieve items from a specific dataset.

        Args:
            dataset_name: Name of the dataset to retrieve items from

        Returns:
            List of dataset items
        """
        pass

    def setup_evaluation_context(self, item: T_Item) -> None:
        """
        Set up context for evaluating an item.

        Default implementation is a no-op. Override for provider-specific
        setup before evaluation.

        Args:
            item: The evaluation item to set up context for
        """
        return None

    def get_observation_context(self, item: T_Item, run_name: str) -> Any:
        """
        Get a context manager for observing an item's evaluation.

        Default implementation returns a no-op context manager.
        Override for provider-specific observation support.

        Args:
            item: The evaluation item to observe
            run_name: Name for the evaluation run

        Returns:
            A context manager for the observation
        """
        return nullcontext()
