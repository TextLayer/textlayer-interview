from typing import Tuple

from flask import request

from app.errors import ValidationException


def get_arg(arg_name, type=str, default=None):
    if request.args and arg_name in request.args:
        try:
            return type(request.args[arg_name])
        except ValueError as err:
            raise ValidationException(f"Unable to parse {arg_name} as {type}") from err
    else:
        return default


def get_pagination_args(default_page=1, default_per_page=10, max_per_page=1000) -> Tuple[int, int]:
    """Get pagination arguments from request args

    Args:
        default_page (int, optional): default page number. Defaults to 1.
        default_per_page (int, optional): default items per page. Defaults to 10.
        max_per_page (int, optional): max items per page. Defaults to 1000.

    Returns:
        Tuple[int, int]: page number, items per page
    """
    page = request.args.get("page", type=int, default=default_page)
    per_page = request.args.get("per_page", type=int, default=default_per_page)

    # Ensure per_page is within the allowed range
    per_page = min(per_page, max_per_page)
    return page, per_page
