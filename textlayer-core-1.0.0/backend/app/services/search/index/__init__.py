from typing import Any, Dict, Optional

from flask import current_app
from opensearchpy import (
    # required to avoid with built-in ConnectionError exception
    ConnectionError as OSConnectionError,
)
from opensearchpy import NotFoundError, OpenSearch, RequestError

from app import logger

BASE_TEMPLATE = {
    "index": "",
    "body": {
        "settings": {
            "number_of_shards": current_app.config["OPENSEARCH_SHARDS"],
            "number_of_replicas": current_app.config["OPENSEARCH_REPLICAS"],
        },
        "mappings": {"properties": {}},
    },
}


def create_index(session: OpenSearch, template: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create an OpenSearch index.

    Args:
        session (OpenSearch): The OpenSearch session object.
        template (Dict[str, Any]): The template containing the index name and body.

    Returns:
        Optional[Dict[str, Any]]: The response object from OpenSearch if successful, else None.
    """
    try:
        response = session.indices.create(index=template["index"], body=template["body"])
        logger.info(f"Index '{template['index']}' created successfully.")
        return response
    except RequestError as err:
        logger.error(f"Failed to create index '{template['index']}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while creating index '{template['index']}': {err}")
    return None


def delete_index(session: OpenSearch, index: str) -> bool:
    """
    Delete an OpenSearch index.

    Args:
        session (OpenSearch): The OpenSearch session object.
        index (str): The index name to delete.

    Returns:
        bool: True if the index was deleted successfully, False otherwise.
    """
    try:
        session.indices.delete(index=index)
        logger.info(f"Index '{index}' deleted successfully.")
        return True
    except NotFoundError:
        logger.warning(f"Index '{index}' not found. Nothing to delete.")
    except RequestError as err:
        logger.error(f"Failed to delete index '{index}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while deleting index '{index}': {err}")
    return False


def index_exists(session: OpenSearch, index: str) -> bool:
    """
    Check if an OpenSearch index exists.

    Args:
        session (OpenSearch): The OpenSearch session object.
        index (str): The index name.

    Returns:
        bool: True if the index exists, False otherwise.
    """
    try:
        exists = session.indices.exists(index=index)
        return exists
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while checking index '{index}': {err}")
    return False


def reindex(session: OpenSearch, source_index: str, target_index: str) -> Optional[Dict[str, Any]]:
    """
    Reindex documents from one index to another in OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session object.
        source_index (str): The name of the source index.
        target_index (str): The name of the target index.

    Returns:
        Optional[Dict[str, Any]]: The response object from OpenSearch if successful, else None.
    """
    try:
        response = session.reindex(
            body={"source": {"index": source_index}, "dest": {"index": target_index}},
            wait_for_completion=True,
        )
        logger.info(f"Successfully reindexed from '{source_index}' to '{target_index}'.")
        return response
    except RequestError as err:
        logger.error(f"Failed to reindex from '{source_index}' to '{target_index}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while reindexing from '{source_index}' to '{target_index}': {err}")
    return None
