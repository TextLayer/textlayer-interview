import logging

from flask import request

from app import logger


def log_request_info():
    if logger.isEnabledFor(logging.INFO):
        logger.info(request.headers)
        logger.info(request.get_json(silent=True))


def log_response_info(response):
    if logger.isEnabledFor(logging.INFO):
        try:
            # Only log response data for non-static file responses
            if hasattr(response, 'data') and not response.direct_passthrough:
                logger.info(response.data)
            else:
                logger.info(f"Response: {response.status_code} - {response.status}")
        except (RuntimeError, AttributeError) as e:
            # Handle cases where response data cannot be accessed
            logger.info(f"Response: {response.status_code} - {response.status} (data not accessible: {str(e)})")
    return response
