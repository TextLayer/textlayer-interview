import os
import sys
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import click
from dotenv import load_dotenv

from app import create_app, logger

#
# Application initialization
#

# Initialize code coverage if needed
COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage

    COV = coverage.coverage(branch=True, include="app/*")
    COV.start()

# Load environment variables from .env file if it exists
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Create the Flask application using environment config or default to DEV
app = create_app(os.getenv("FLASK_CONFIG") or "DEV")


#
# Helper functions
#


def run_tests(coverage: bool, test_names: tuple) -> Any:
    """
    Run the unit tests with optional coverage reporting.

    Args:
        coverage: Whether to run tests with code coverage
        test_names: Specific test names to run

    Returns:
        An object with a wasSuccessful method indicating test success
    """
    # If coverage is requested but not enabled, restart with coverage enabled
    if coverage and not os.environ.get("FLASK_COVERAGE"):
        import subprocess

        os.environ["FLASK_COVERAGE"] = "1"
        sys.exit(subprocess.call(sys.argv))

    # Run tests with pytest
    import pytest

    os.environ["FLASK_CONFIG"] = "TEST"
    args = ["tests"] if not test_names else list(test_names)
    exit_code = pytest.main(args)

    # Generate coverage report if enabled
    if COV:
        COV.stop()
        COV.save()
        logger.info("Coverage Summary:")
        COV.report()

        # Generate HTML coverage report
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, "tmp/coverage")
        COV.html_report(directory=covdir)
        logger.info("HTML version: file://%s/index.html" % covdir)
        COV.erase()

    # Create a test result object for the caller
    class MockTestResult:
        def wasSuccessful(self):
            return exit_code == 0

    return MockTestResult()


def init_opensearch() -> bool:
    """
    Initialize OpenSearch indices if they don't exist.

    Returns:
        True if initialization was successful
    """
    from app.services.search import opensearch_session
    from app.services.search.index import create_index
    from app.services.search.index.chat_messages_index import chat_messages_index

    # Define indices to create
    chat_messages_schema = chat_messages_index()
    indices = [
        chat_messages_schema,
    ]

    # Create session and initialize indices
    session = opensearch_session()
    for index in indices:
        index_name = index["index"]
        if not index_name:
            raise ValueError("Index name is required")
        if not session.indices.exists(index=index_name):
            create_index(session, index)

    click.echo("OpenSearch initialized")
    return True


#
# CLI Commands
#


@app.cli.command()
@click.option(
    "--coverage/--no-coverage",
    default=False,
    help="Run tests under code coverage.",
)
@click.argument("test_names", nargs=-1)
def test(coverage: bool, test_names: tuple) -> None:
    """
    Run the unit tests.

    Args:
        coverage: Whether to run tests with code coverage
        test_names: Specific test names to run
    """
    # Run the tests and get results
    test_results = run_tests(coverage, test_names)

    # Exit with appropriate status code
    sys.exit(0 if test_results.wasSuccessful() else 1)


@app.cli.command()
def init_search():
    """Initialize search indices in OpenSearch."""
    try:
        success = init_opensearch()
        sys.exit(0 if success else 1)
    except Exception as e:
        click.echo(f"Error initializing search: {e}")
        sys.exit(1)


@app.cli.command()
@click.argument("dataset_names", nargs=-1, required=False)
@click.option("--run-version", default=None, help="Version identifier for this test run")
@click.option("--quiet/--no-quiet", default=False, help="Suppress progress output")
@click.option("--use-prompt-label", default="test", help="Prompt label to use for this test run")
def run_evals(
    dataset_names: tuple, run_version: Optional[str] = None, quiet: bool = False, use_prompt_label: str = "test"
) -> None:
    """
    Run evaluations on datasets using the configured eval provider.

    Examples:
        flask run_evals my_dataset
        flask run_evals dataset1 dataset2 dataset3
        flask run_evals dataset1 --run-version=v1.0
        flask run_evals --quiet dataset1

        # Add a prompt label to the run
        $ flask run_evals dataset1 --run-prompt-label=production

        # Add a prompt label to the run
        $ flask run_evals dataset1 --run-prompt-label=production

    Args:
        dataset_names: Names of datasets to process
        run_version: Optional version identifier for this run
        quiet: If True, suppress progress output
        use_prompt_label: The label on the prompt to use for this test run
    """
    try:
        # Import required components
        from flask import current_app

        from app.cli.threads.process_chat_message import process_chat_message
        from app.services.llm.evals.client import EvalClient
        from app.services.llm.evals.runner import EvalRunner

        # Initialize evaluation client and runner
        runner = EvalRunner(EvalClient())

        current_app.config["PROMPT_LABEL"] = use_prompt_label

        # Get datasets, filtered by name if specified
        datasets = runner.get_datasets(dataset_names)
        if not datasets:
            click.echo("No datasets found matching the specified names.")
            sys.exit(1)

        if not quiet:
            click.echo(f"Found {len(datasets)} datasets")

        # Create run identifiers
        run_timestamp = datetime.now().strftime("%Y-%m-%d")
        version_tag = f"[{run_version}]" if run_version else f"[{str(uuid4())[:8]}]"

        # Process all datasets
        runner.process_datasets(
            datasets=datasets,
            processor_func=process_chat_message,
            run_timestamp=run_timestamp,
            version_tag=version_tag,
            quiet=quiet,
        )

        sys.exit(0)
    except Exception as e:
        click.echo(f"Error running evaluations: {e}")
        sys.exit(1)


@app.cli.command()
def process_chat_message():
    """Process a test chat message with the current LLM configuration."""
    try:
        from app.cli.threads.process_chat_message import process_chat_message

        # Create initial messages list
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Process the message and get the response
        response = process_chat_message(messages)

        # Print the assistant's response to the console
        click.echo(f"Assistant: {response['content']}")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}")
        sys.exit(1)


@app.cli.command()
def chat():
    """Chat with the bot via CLI."""
    from app.cli.threads.process_chat_message import process_chat_message

    # Initialize chat history
    chat_history = []

    try:
        while True:
            # Take user input
            user_input = input("You: ")

            # Exit the chat if the user types 'exit'
            if user_input.lower() == "exit":
                print("Exiting chat. Goodbye!")
                break

            # Add user input to chat history
            chat_history.append({"role": "user", "content": user_input})

            # Process the input message with the entire chat history
            response = process_chat_message(chat_history)["content"]  # TODO: check if openai needs this

            # Add bot response to chat history
            chat_history.append({"role": "assistant", "content": response})

            # Display the bot's response
            print(f"Bot: {response}")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
