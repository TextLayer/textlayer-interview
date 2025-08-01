from typing import Any, Dict, List, Optional

from opensearchpy import (
    # required to avoid with built-in ConnectionError exception
    ConnectionError as OSConnectionError,
)
from opensearchpy import (
    NotFoundError,
    OpenSearch,
    RequestError,
)

from app import logger


def entry_exists(session: OpenSearch, document_id: str, index: str) -> bool:
    """
    Check if a document exists in OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        document_id (str): The document ID.
        index (str): The index to check.

    Returns:
        bool: True if the document exists, False otherwise.
    """
    try:
        exists = session.exists(index=index, id=document_id)
        logger.info(f"Checked existence of document '{document_id}' in index '{index}': {exists}")
        return exists
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while checking existence of document '{document_id}': {err}")
    except RequestError as err:
        logger.error(f"Request error when checking document existence '{document_id}': {err}")
    return False


def get_entry_by_id(session: OpenSearch, document_id: str, index: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a document by ID from OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        document_id (str): The document ID.
        index (str): The index to query.

    Returns:
        Optional[Dict[str, Any]]: The document if found, else None.
    """
    try:
        document = session.get(index=index, id=document_id)
        logger.info(f"Retrieved document '{document_id}' from index '{index}'.")
        return document
    except NotFoundError:
        logger.warning(f"Document '{document_id}' not found in index '{index}'.")
    except RequestError as err:
        logger.error(f"Request error when retrieving document '{document_id}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while retrieving document '{document_id}': {err}")
    return None


def term_vector(session: OpenSearch, document_id: str, index: str, fields: List[str]) -> Optional[Dict[str, Any]]:
    """
    Retrieve the term vector for a document.

    Args:
        session (OpenSearch): The OpenSearch session.
        document_id (str): The document ID.
        index (str): The index where the document is stored.
        fields (List[str]): The fields to retrieve term vectors for.

    Returns:
        Optional[Dict[str, Any]]: The term vector response if successful, else None.
    """
    try:
        response = session.termvectors(index=index, id=document_id, fields=fields, term_statistics=True)
        logger.info(f"Retrieved term vector for document '{document_id}' in index '{index}'.")
        return response
    except NotFoundError:
        logger.warning(f"Document '{document_id}' not found in index '{index}' for term vector retrieval.")
    except RequestError as err:
        logger.error(f"Request error when retrieving term vector for document '{document_id}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while retrieving term vector for document '{document_id}': {err}")
    return None


def multi_get_term_vectors(session: OpenSearch, index: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Retrieve term vectors for multiple documents.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index to query.
        query (Dict[str, Any]): The query defining which documents to retrieve term vectors for.

    Returns:
        Optional[Dict[str, Any]]: The term vectors if successful, else None.
    """
    try:
        response = session.mtermvectors(index=index, body=query)
        logger.info("Retrieved term vectors for multiple documents.")
        return response
    except RequestError as err:
        logger.error(f"Request error when retrieving multiple term vectors: {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while retrieving multiple term vectors: {err}")
    return None
