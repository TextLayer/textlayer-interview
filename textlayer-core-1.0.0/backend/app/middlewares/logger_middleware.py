import logging

from flask import request

from app import logger


def log_request_info():
    if logger.isEnabledFor(logging.INFO):
        logger.info(request.headers)
        logger.info(request.get_json(silent=True))


def log_response_info(response):
    if logger.isEnabledFor(logging.INFO):
        # Check if it's a streaming response before trying to access data
        if hasattr(response, "direct_passthrough") and response.direct_passthrough:
            logger.info("Streaming response (data not logged)")
        else:
            logger.info(response.data)
    return response
