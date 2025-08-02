from typing import Any, Dict, List, Optional, Tuple

from opensearchpy import (
    # required to avoid with built-in ConnectionError exception
    ConnectionError as OSConnectionError,
)
from opensearchpy import NotFoundError, OpenSearch, RequestError, helpers

from app import logger


def update_entry(
    session: OpenSearch,
    index: str,
    document_id: str,
    body: Optional[Dict[str, Any]] = None,
    script: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update a document in OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index where the document is stored.
        document_id (str): The ID of the document to update.
        body (Optional[Dict[str, Any]], optional): Partial update fields.
        script (Optional[str], optional): A Painless script for the update.
        params (Optional[Dict[str, Any]], optional): Parameters for the script.

    Returns:
        Optional[Dict[str, Any]]: The updated document response if successful, else None.
    """
    update_body = {}

    if body:
        update_body["doc"] = body

    if script:
        update_body["script"] = {"source": script, "lang": "painless"}
        if params:
            update_body["script"]["params"] = params

    try:
        response = session.update(index=index, id=document_id, body=update_body, retry_on_conflict=3)
        logger.info(f"Document with ID '{document_id}' updated in index '{index}'.")
        return response
    except NotFoundError:
        logger.warning(f"Document with ID '{document_id}' not found in index '{index}'.")
    except RequestError as err:
        logger.error(f"Failed to update document '{document_id}' in index '{index}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error while updating document '{document_id}' in index '{index}': {err}")
    return None


def bulk_update(
    session: OpenSearch,
    index: str,
    body: List[Dict[str, Any]],
    request_timeout: int = 180,
) -> Optional[Tuple[int, List[Any]]]:
    """
    Bulk update multiple documents in OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index where the documents are stored.
        body (List[Dict[str, Any]]): List of document updates (each containing `id` and update fields).
        request_timeout (int, optional): Timeout for the bulk operation. Defaults to 180 seconds.

    Returns:
        Optional[Tuple[int, List[Any]]]: Number of successfully updated documents and a list of errors.
    """
    if not body:
        logger.warning(f"No documents provided for bulk update in index '{index}'.")
        return None

    bulk_actions = [{"_op_type": "update", "_index": index, "_id": doc["id"], "doc": doc} for doc in body]

    try:
        success_count, errors = helpers.bulk(session, bulk_actions, request_timeout=request_timeout)
        logger.info(f"Bulk update: {success_count} documents updated in index '{index}'.")

        if errors:
            logger.warning(f"Bulk update in '{index}' completed with {len(errors)} errors.")
        return success_count, errors
    except RequestError as err:
        logger.error(f"Bulk update failed for index '{index}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error during bulk update in index '{index}': {err}")
    return None


def update_by_query(
    session: OpenSearch,
    index: str,
    query: Dict[str, Any],
    body_update: str,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update multiple documents in OpenSearch using a query.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index where the documents are stored.
        query (Dict[str, Any]): The query to filter documents for update.
        body_update (str): The update script (Painless).
        params (Optional[Dict[str, Any]], optional): Parameters for the script.

    Returns:
        Optional[Dict[str, Any]]: The OpenSearch response if successful, else None.
    """
    body = {"query": query, "script": {"source": body_update, "lang": "painless"}}

    if params:
        body["script"]["params"] = params

    try:
        response = session.update_by_query(index=index, body=body, conflicts="proceed")
        updated_count = response.get("updated", 0)
        logger.info(f"Updated {updated_count} documents in index '{index}' using query.")
        return response
    except RequestError as err:
        logger.error(f"Failed to update documents in index '{index}' with query {query}: {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error during update by query in index '{index}': {err}")
    return None


def bulk_upsert(
    session: OpenSearch,
    index: str,
    body: List[Dict[str, Any]],
    request_timeout: int = 180,
) -> Optional[Tuple[int, List[Any]]]:
    """
    Bulk upsert (update or insert) multiple documents in OpenSearch.

    Args:
        session (OpenSearch): The OpenSearch session.
        index (str): The index where the documents are stored.
        body (List[Dict[str, Any]]): List of documents to upsert.
        request_timeout (int, optional): Timeout for the bulk operation. Defaults to 180 seconds.

    Returns:
        Optional[Tuple[int, List[Any]]]: Number of successfully upserted documents and a list of errors.
    """
    if not body:
        logger.warning(f"No documents provided for bulk upsert in index '{index}'.")
        return None

    bulk_actions = [
        {
            "_op_type": "update",
            "_index": index,
            "_id": doc["id"],
            "doc": doc,
            "doc_as_upsert": True,  # If the document doesn't exist, create it
        }
        for doc in body
    ]

    try:
        success_count, errors = helpers.bulk(session, bulk_actions, request_timeout=request_timeout)
        logger.info(f"Bulk upsert: {success_count} documents upserted in index '{index}'.")

        if errors:
            logger.warning(f"Bulk upsert in '{index}' completed with {len(errors)} errors.")
        return success_count, errors
    except RequestError as err:
        logger.error(f"Bulk upsert failed for index '{index}': {err}")
    except OSConnectionError as err:
        logger.error(f"OpenSearch connection error during bulk upsert in index '{index}': {err}")
    return None
