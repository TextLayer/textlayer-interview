from typing import Optional

import boto3
from flask import current_app


def boto3_session(region_name: Optional[str] = None) -> boto3.Session:
    """
    Create and return a boto3 session for the specified AWS region.

    If no region is provided, the function uses the region from the Flask application's configuration.

    Args:
        region_name (Optional[str]): The AWS region name. If not provided, defaults to the region set in Flask config.

    Returns:
        boto3.Session: A configured boto3 session object.
    """
    region_name = region_name or current_app.config["AWS_REGION"]

    return boto3.Session(
        region_name=region_name,
        aws_access_key_id=current_app.config["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["AWS_SECRET_ACCESS_KEY"],
    )
