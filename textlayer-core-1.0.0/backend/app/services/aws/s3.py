from typing import Any, Dict, Optional, Union

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import current_app

from app import logger


def _get_bucket(bucket: Optional[str]) -> str:
    """
    Retrieve the S3 bucket name.

    If a bucket name is provided, it returns that. Otherwise, it
    fetches the default bucket name from Flask's configuration.

    Args:
        bucket (Optional[str]): An optional S3 bucket name.

    Returns:
        str: The resolved S3 bucket name.
    """
    return bucket or current_app.config.get("S3_BUCKET")


def _get_region(region: Optional[str]) -> str:
    """
    Retrieve the AWS region.

    If a region is provided, it returns that. Otherwise, it
    fetches the default region from Flask's configuration.

    Args:
        region (Optional[str]): An optional AWS region name.

    Returns:
        str: The resolved AWS region name.
    """
    return region or current_app.config["AWS_REGION"]


def _log_error(error: Exception, key: str) -> None:
    """
    Log the given error along with the S3 key involved.

    Args:
        error (Exception): The exception that occurred.
        key (str): The S3 key associated with the error.
    """
    logger.error(f"Boto3 Client Error: {error} for Key: {key}")


def document_exists(session: boto3.Session, key: str, bucket: Optional[str] = None) -> bool:
    """
    Check if a document (object) exists in an S3 bucket.

    Args:
        session (boto3.Session): A boto3 session object.
        key (str): The S3 object key (path within the bucket).
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.

    Returns:
        bool: True if the object exists, False otherwise.
    """
    bucket_name = _get_bucket(bucket)
    try:
        s3_client = session.client("s3")
        s3_client.head_object(Bucket=bucket_name, Key=key)
    except ClientError as err:
        error_code = err.response.get("Error", {}).get("Code")
        if error_code == "404":
            # The object does not exist
            return False
        _log_error(err, key)
        return False
    return True


def get_document(session: boto3.Session, key: str, bucket: Optional[str] = None) -> Union[Dict[str, Any], bool]:
    """
    Retrieve a document (object) from an S3 bucket.

    Args:
        session (boto3.Session): A boto3 session object.
        key (str): The S3 object key.
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.

    Returns:
        Union[Dict[str, Any], bool]:
            A dictionary containing the S3 object metadata and body
            if the request is successful, or False on error.
    """
    bucket_name = _get_bucket(bucket)
    try:
        s3_client = session.client("s3")
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response
    except ClientError as err:
        _log_error(err, key)
        return False


def delete_document(session: boto3.Session, key: str, bucket: Optional[str] = None) -> bool:
    """
    Delete a document (object) from an S3 bucket.

    Args:
        session (boto3.Session): A boto3 session object.
        key (str): The S3 object key.
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.

    Returns:
        bool: True if the deletion was successful, False otherwise.
    """
    bucket_name = _get_bucket(bucket)
    try:
        s3_client = session.client("s3")
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as err:
        _log_error(err, key)
        return False


def upload_document(
    session: boto3.Session,
    key: str,
    body: Any,
    bucket: Optional[str] = None,
    content_type: str = "binary/octet-stream",
) -> bool:
    """
    Upload a document (object) to an S3 bucket.

    Args:
        session (boto3.Session): A boto3 session object.
        key (str): The S3 object key.
        body (Any): The content to be uploaded.
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.
        content_type (str): The MIME type of the file.

    Returns:
        bool: True if the upload was successful, False otherwise.
    """
    bucket_name = _get_bucket(bucket)
    try:
        s3_client = session.client("s3")
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body, ContentType=content_type)
        return True
    except ClientError as err:
        _log_error(err, key)
        return False


def copy_document(
    session: boto3.Session,
    document: Any,
    from_bucket: str,
    original_key: str,
    to_bucket: Optional[str] = None,
    new_key: Optional[str] = None,
    metadata_directive: str = "COPY",
    content_type: str = "application/pdf",
) -> bool:
    """
    Copy a document (object) from one S3 bucket to another.

    Args:
        session (boto3.Session): A boto3 session object.
        document (Any): An object expected to have an 's3_key' attribute, if new_key is not provided.
        from_bucket (str): The name of the source S3 bucket.
        original_key (str): The key (path) of the document to copy from the source bucket.
        to_bucket (Optional[str]): The name of the destination S3 bucket. If not provided,
            this is pulled from Flask's config.
        new_key (Optional[str]): The key (path) for the copied document. Defaults to
            `document.s3_key` if not provided.
        metadata_directive (str): COPY or REPLACE. Indicates whether to copy existing metadata
            or replace it with new metadata.
        content_type (str): The MIME type to set for the copied document.

    Returns:
        bool: True if the copy was successful, False otherwise.
    """
    bucket_name = _get_bucket(to_bucket)
    resolved_new_key = new_key or getattr(document, "s3_key", None)
    copy_source = {"Bucket": from_bucket, "Key": original_key}

    try:
        s3_client = session.client("s3")
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=bucket_name,
            Key=resolved_new_key,
            MetadataDirective=metadata_directive,
            ContentType=content_type,
        )
        return True
    except ClientError as err:
        _log_error(err, str(resolved_new_key))
        return False


def generate_presigned_post(
    session: boto3.Session,
    key: str,
    bucket: Optional[str] = None,
    region: Optional[str] = None,
    expiration: int = 3600,
) -> Union[Dict[str, Any], bool]:
    """
    Generate a presigned POST dictionary for uploading a file to S3 directly from a client.

    Args:
        session (boto3.Session): A boto3 session object.
        key (str): The S3 object key.
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.
        region (Optional[str]): An optional AWS region. If not provided,
            this is pulled from Flask's config.
        expiration (int): Expiration time in seconds for the presigned URL.

    Returns:
        Union[Dict[str, Any], bool]: A dictionary containing fields and the URL
        needed for the POST if successful, or False on error.
    """
    bucket_name = _get_bucket(bucket)
    region_name = _get_region(region)

    try:
        s3_client = session.client("s3", config=Config(signature_version="s3v4"), region_name=region_name)
        response = s3_client.generate_presigned_post(Bucket=bucket_name, Key=key, ExpiresIn=expiration)
        return response
    except ClientError as err:
        _log_error(err, key)
        return False


def generate_presigned_get(
    session: boto3.Session,
    object_name: str,
    bucket: Optional[str] = None,
    region: Optional[str] = None,
    expiration: int = 3600,
) -> Union[str, bool]:
    """
    Generate a presigned GET URL for downloading a file from S3.

    Args:
        session (boto3.Session): A boto3 session object.
        object_name (str): The S3 object key.
        bucket (Optional[str]): An optional S3 bucket name. If not provided,
            this is pulled from Flask's config.
        region (Optional[str]): An optional AWS region. If not provided,
            this is pulled from Flask's config.
        expiration (int): Expiration time in seconds for the presigned URL.

    Returns:
        Union[str, bool]: The presigned URL as a string if successful, or False on error.
    """
    bucket_name = _get_bucket(bucket)
    region_name = _get_region(region)

    try:
        s3_client = session.client("s3", config=Config(signature_version="s3v4"), region_name=region_name)
        response = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expiration,
        )
        return response
    except ClientError as err:
        _log_error(err, object_name)
        return False
