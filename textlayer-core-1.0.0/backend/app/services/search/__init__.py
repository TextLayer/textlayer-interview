from typing import Optional

from flask import current_app
from opensearchpy import (
    # required to avoid with built-in ConnectionError exception
    ConnectionError as OSConnectionError,
)
from opensearchpy import OpenSearch

from app import logger


def opensearch_session() -> Optional[OpenSearch]:
    """
    Creates and returns an OpenSearch session.

    Ensures the necessary configuration values are set before attempting to
    connect. Logs errors if connection fails or if configuration is missing.

    Returns:
        Optional[OpenSearch]: A configured OpenSearch session if successful, otherwise None.
    """
    try:
        # Retrieve necessary configurations
        os_host = current_app.config.get("OPENSEARCH_HOST")
        os_user = current_app.config.get("OPENSEARCH_USER")
        os_password = current_app.config.get("OPENSEARCH_PASSWORD")
        os_port = current_app.config["OPENSEARCH_PORT"]

        if not os_host or not os_user or not os_password:
            logger.error("Missing OpenSearch configuration values.")
            return None

        session = OpenSearch(
            hosts=[{"host": os_host, "port": os_port}],
            http_auth=(os_user, os_password),
            use_ssl=True,  # or False depending on your endpoint
            verify_certs=True,  # or False in dev
            ssl_assert_hostname=False,
            ssl_show_warn=False,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )
        logger.info(f"Connected to OpenSearch at {os_host}.")
        return session

    except OSConnectionError as err:
        logger.error(f"Failed to connect to OpenSearch: {err}")
    except Exception as err:
        logger.error(f"Unexpected error while creating OpenSearch session: {err}")

    return None
