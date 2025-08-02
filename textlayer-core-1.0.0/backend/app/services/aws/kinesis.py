import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app import logger


def send_message_to_kinesis_firehose(session: boto3.Session, data: Any, stream_name: str) -> bool:
    """
    Send a message to an AWS Kinesis Firehose delivery stream.

    Args:
        session (boto3.Session): A boto3 session object.
        data (Any): The data payload to be sent.
        stream_name (str): The name of the Kinesis Firehose delivery stream.

    Returns:
        bool: True if the message was successfully sent, False otherwise.
    """
    try:
        kinesis_client = session.client("firehose")
        kinesis_client.put_record(DeliveryStreamName=stream_name, Record={"Data": json.dumps(data)})
        return True
    except ClientError as err:
        logger.error(f"Boto3 Client Error: {err} | Stream Name: {stream_name}")
        return False
