from typing import Any, Dict, List, Union
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from flask import current_app
from ratelimiter import RateLimiter

from app import logger


def create_batch(iterable: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Splits an iterable into smaller batches of a given size.

    Args:
        iterable (List[Any]): The list to be split into batches.
        batch_size (int): The maximum size of each batch.

    Returns:
        List[List[Any]]: A list of batches.
    """
    if not iterable:
        return []

    return [iterable[i : i + batch_size] for i in range(0, len(iterable), batch_size)]


def send_task_to_batch(
    session: boto3.Session,
    job_queue: str,
    job_definition: str,
    job_name: str,
    command: List[str],
    vcpus: float = 1.0,
    memory: int = 2048,
) -> Union[Dict[str, Any], bool]:
    """
    Submits a task to AWS Batch.

    Args:
        session (boto3.Session): The boto3 session object.
        job_queue (str): The AWS Batch job queue name.
        job_definition (str): The AWS Batch job definition name.
        job_name (str): The name of the job.
        command (List[str]): The command to execute within the container.
        vcpus (float, optional): Number of vCPUs to allocate. Defaults to 1.0.
        memory (int, optional): Memory (in MB) to allocate. Defaults to 2048.

    Returns:
        Union[Dict[str, Any], bool]: The AWS Batch response if successful, otherwise False.
    """
    try:
        batch_client = session.client("batch")
        environment_vars = [
            {"name": k, "value": v}
            for k, v in current_app.config.items()
            if k in current_app.config.get("ENV_VARS", [])
        ]

        response = batch_client.submit_job(
            jobName=job_name,
            jobQueue=job_queue,
            jobDefinition=job_definition,
            containerOverrides={
                "command": command,
                "environment": environment_vars,
                "resourceRequirements": [
                    {"value": str(vcpus), "type": "VCPU"},
                    {"value": str(memory), "type": "MEMORY"},
                ],
            },
        )
        return response

    except ClientError as err:
        logger.error(f"Boto3 Client Error: {err}")
        return False


def send_tasks_to_batch(session: boto3.Session, batch_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Submits multiple batch tasks to AWS Batch while adhering to rate limits.

    Args:
        session (boto3.Session): The boto3 session object.
        batch_tasks (List[Dict[str, Any]]): A list of batch task parameters.

    Returns:
        List[Dict[str, Any]]: A list of AWS Batch responses.
    """
    rate_limiter = RateLimiter(max_calls=65, period=1)
    responses: List[Dict[str, Any]] = []

    for batch_task in batch_tasks:
        with rate_limiter:
            if not current_app.config.get("TESTING", False):
                response = send_task_to_batch(
                    session=session,
                    job_queue=batch_task["job_queue"],
                    job_definition=batch_task["job_definition"],
                    job_name=batch_task["job_name"],
                    command=batch_task["command"],
                    vcpus=batch_task.get("vcpus", 1.0),
                    memory=batch_task.get("memory", 2048),
                )
                if response:
                    responses.append(response)
            else:
                responses.append({"jobId": str(uuid4())})

    return responses
