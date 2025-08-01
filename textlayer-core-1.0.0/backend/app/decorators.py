import traceback
from functools import wraps

from marshmallow import ValidationError

from app import logger
from app.errors import ProcessingException, ValidationException
from app.utils.messages import Error
from app.utils.response import Response


def handle_exceptions(func):
    """
    Decorator for standardized exception handling in API endpoints.

    This decorator catches various types of exceptions that might occur during
    request processing and converts them into appropriate API responses with
    consistent error formatting. It ensures that all API endpoints have uniform
    error handling behavior.

    Handled exception types:
    - ProcessingException: For errors during data processing
    - ValidationException: For custom validation errors
    - ValidationError: For Marshmallow schema validation errors
    - Exception: For all other unexpected errors

    Example:
        @blueprint.route('/users', methods=['POST'])
        @handle_exceptions
        def create_user():
            return jsonify({"status": "success"})

    Args:
        func: The function to wrap with exception handling

    Returns:
        A wrapped function that includes standardized exception handling
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
        Wrapper function that executes the decorated function within a try-except block.

        Args:
            *args: Positional arguments to pass to the decorated function
            **kwargs: Keyword arguments to pass to the decorated function

        Returns:
            Either the original function's return value if no exceptions occur,
            or an appropriate error response if an exception is caught
        """
        try:
            return func(*args, **kwargs)
        except ProcessingException as pe:
            logger.info(pe)
            return Response.make(pe.messages, Response.HTTP_BAD_REQUEST)
        except ValidationException as ve:
            logger.info(str(ve))
            return Response.make(ve.messages, Response.HTTP_BAD_REQUEST)
        except ValidationError as err:
            logger.info(err)
            return Response.make(err.messages, Response.HTTP_BAD_REQUEST)
        except Exception as e:
            traceback.print_exc()
            logger.error(f"general exception {e}")
            return Response.make(Error.REQUEST_FAILED, Response.HTTP_ERROR)

    return wrapper
