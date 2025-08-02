import os

import pytest

from app import create_app

# Set test environment
os.environ["FLASK_CONFIG"] = "TEST"


@pytest.fixture(scope="session")
def app():
    """Create and configure a Flask app for testing."""
    app = create_app("TEST")
    yield app


@pytest.fixture(scope="session")
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope="session")
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()
