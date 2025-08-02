import json
import uuid
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from app import logger


def send_message_to_sqs(session: boto3.Session, queue_url: str, message: Any, fifo: bool = False) -> bool:
    """
    Send a message to an AWS SQS queue (Standard or FIFO).

    Args:
        session (boto3.Session): A boto3 session object.
        queue_url (str): The SQS queue URL.
        message (Any): The message to send.
        fifo (bool, optional): Set to True for FIFO queues, False for standard queues. Defaults to False.

    Returns:
        bool: True if the message was sent successfully, False otherwise.
    """
    try:
        sqs_client = session.client("sqs")
        message_body = json.dumps(message)
        send_params: Dict[str, Any] = {
            "QueueUrl": queue_url,
            "MessageBody": message_body,
        }

        # Determine if the queue is FIFO based on the URL or the `fifo` flag
        is_fifo = fifo or queue_url.endswith(".fifo")

        if is_fifo:
            send_params["MessageGroupId"] = str(uuid.uuid4())  # Required for FIFO queues

        sqs_client.send_message(**send_params)
        return True

    except ClientError as err:
        logger.error(f"Boto3 Client Error: {err} | Queue URL: {queue_url}")
        return False
