from typing import Any, Dict, Optional

from opensearchpy import (
    # required to avoid with built-in ConnectionError exception
    ConnectionError as ESConnectionError,
)
from opensearchpy import (
    NotFoundError,
    OpenSearch,
    RequestError,
)

from app import logger


def delete_entry(session: OpenSearch, document_id: str, index: str) -> Optional[Dict[str, Any]]:
    """
    Delete a document from OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        document_id (str): The ID of the document to delete.
        index (str): The index from which to delete the document.

    Returns:
        Optional[Dict[str, Any]]: The response from OpenSearch if successful, else None.
    """
    try:
        response = session.delete(index=index, id=document_id)
        logger.info(f"Document with ID '{document_id}' deleted from index '{index}'.")
        return response
    except NotFoundError:
        logger.warning(f"Document with ID '{document_id}' not found in index '{index}'.")
    except RequestError as err:
        logger.error(f"Failed to delete document with ID '{document_id}' in index '{index}': {err}")
    except ESConnectionError as err:
        logger.error(f"OpenSearch connection error while deleting document '{document_id}' in index '{index}': {err}")
    return None


def delete_by_query(session: OpenSearch, index: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Delete documents from OpenSearch using a query.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index from which to delete documents.
        query (Dict[str, Any]): The query used to filter documents for deletion.

    Returns:
        Optional[Dict[str, Any]]: The response from OpenSearch if successful, else None.
    """
    try:
        response = session.delete_by_query(index=index, body=query)
        deleted_count = response.get("deleted", 0)
        logger.info(f"Deleted {deleted_count} documents from index '{index}' using query.")
        return response
    except RequestError as err:
        logger.error(f"Failed to delete documents in index '{index}' with query {query}: {err}")
    except ESConnectionError as err:
        logger.error(f"OpenSearch connection error while deleting by query in index '{index}': {err}")
    return None
