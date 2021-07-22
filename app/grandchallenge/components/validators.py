from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.utils._os import safe_join


def validate_safe_path(value):
    """Ensures that the path is safe and normalised."""
    base = "/input/"

    try:
        new_path = safe_join(base, value)
    except SuspiciousFileOperation:
        raise ValidationError("Relative paths are not allowed.")

    valid_path = new_path[len(base) :]

    if value != valid_path:
        raise ValidationError(f"Invalid file path, should be {valid_path}.")


def validate_no_slash_at_ends(value):
    if value[0] == "/" or value[-1] == "/":
        raise ValidationError("Path must not begin or end with '/'")
