from typing import Any, Callable, List, Optional

import click
from tqdm import tqdm

from app import logger
from app.services.llm.evals.client import EvalClient


class EvalRunner:
    """
    Runner for executing evaluations on datasets.

    Handles the high-level workflow of processing datasets, including:
    - Progress tracking and reporting
    - Context setup for each evaluation item
    - Error handling during evaluation

    This separates the application-specific evaluation flow from the
    provider-agnostic client implementation.
    """

    def __init__(self, eval_client: EvalClient) -> None:
        """
        Initialize runner with an evaluation client.

        Args:
            eval_client: The evaluation client to use
        """
        self.client = eval_client

    def process_datasets(
        self,
        datasets: List[Any],
        processor_func: Callable[[Any], Any],
        run_timestamp: str,
        version_tag: str,
        quiet: bool = False,
    ) -> None:
        """
        Process evaluation datasets with the specified processor function.

        Args:
            datasets: List of datasets to process
            processor_func: Function to process each item
            run_timestamp: Timestamp string for the run
            version_tag: Version tag for the run
            quiet: If True, suppress progress output

        Raises:
            Exception: If evaluation processing fails
        """
        for dataset in datasets:
            self._process_dataset(
                dataset=dataset,
                processor_func=processor_func,
                run_timestamp=run_timestamp,
                version_tag=version_tag,
                quiet=quiet,
            )

        if not quiet:
            click.echo("All datasets processed successfully")

    def _process_dataset(
        self,
        dataset: Any,
        processor_func: Callable[[Any], Any],
        run_timestamp: str,
        version_tag: str,
        quiet: bool = False,
    ) -> None:
        """
        Process a single dataset with progress tracking.

        Args:
            dataset: The dataset to process
            processor_func: Function to process each item
            run_timestamp: Timestamp string for the run
            version_tag: Version tag for the run
            quiet: If True, suppress progress output
        """
        # Get active items for this dataset
        items = self.client.get_dataset_items(dataset.name)

        if not quiet:
            click.echo(f"Found {len(items)} items in {dataset.name}")

        if not items:
            return

        # Setup progress bar unless quiet mode is enabled
        item_iter = tqdm(items, desc=f"Processing {dataset.name}") if not quiet else items

        # Process each item
        for item in item_iter:
            try:
                # Create run name for this observation
                run_name = f"{dataset.name} - {run_timestamp}{version_tag}"

                # Setup observation context and process
                with self.client.get_observation_context(item, run_name):
                    # Create messages list with the input
                    messages = [{"role": "user", "content": item.input}]

                    self.client.setup_evaluation_context(item)

                    # Process the messages and get the response
                    processor_func(messages)

            except Exception as e:
                if not quiet:
                    click.echo(f"Error processing item: {e}")
                logger.error(f"Error processing item in {dataset.name}: {e}")

        if not quiet:
            click.echo(f"Finished processing {dataset.name}")

    def get_datasets(self, dataset_names: Optional[List[str]] = None) -> List[Any]:
        """
        Get datasets, filtered by name if specified.

        Args:
            dataset_names: Optional list of dataset names to filter by

        Returns:
            List of matching datasets
        """
        return self.client.get_datasets(dataset_names)
