import os

import pytest

from app import create_app, logger


class BaseTest:
    """Base class for all tests"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Set up test environment before each test and tear down after"""
        logger.info(f"Setting up {self.__class__.__name__}")

        # Make sure you set FLASK_CONFIG to TEST
        os.environ["FLASK_CONFIG"] = "TEST"
        self.app = create_app("TEST")

        self.ctx = self.app.app_context()
        self.ctx.push()

        self.client = self.app.test_client()

        yield

        logger.info(f"Tearing down {self.__class__.__name__}")
        self.ctx.pop()
