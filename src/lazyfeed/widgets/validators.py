import re

# Code extracted from:
# https://github.com/django/django/blob/stable/1.3.x/django/core/validators.py#L45
url_regex = re.compile(
    r"^(?:http|ftp)s?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
    r"localhost|"  # localhost...
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


def is_valid_url(value: str) -> bool:
    """
    Check if the provided string is a valid URL.

    Args:
        value (str): The string to be validated.

    Returns:
        bool: True if the string is a valid URL, False otherwise.
    """

    return re.match(url_regex, value) is not None
