from typing import Tuple

from app.errors import ValidationException


def get_arg(args, arg_name, type=str, default=None):
    if args and arg_name in args:
        try:
            return type(args[arg_name])
        except ValueError:
            raise ValidationException(f"Unable to parse {arg_name} as {type}")
    else:
        return default


def get_pagination_args(args, default_page=1, default_per_page=10, max_per_page=1000) -> Tuple[int, int]:
    page = args.get("page", default=default_page)
    per_page = args.get("per_page", default=default_per_page)

    try:
        # Convert page and per_page to integers
        page = int(page)
        per_page = int(per_page)
    except ValueError as e:
        raise ValidationException("Invalid pagination arguments - page and per_page must be integers")

    # Ensure per_page is within the allowed range
    per_page = min(per_page, max_per_page)
    return page, per_page
