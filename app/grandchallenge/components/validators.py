import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.utils._os import safe_join

from grandchallenge.components import VALIDATION_SCRIPT_DIR
from grandchallenge.components.utils.virtualenvs import run_script_in_venv


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


def validate_relative_path_not_reserved(value):
    if value.casefold() == "inputs.json".casefold():
        raise ValidationError("This relative path is reserved")


def validate_newick_tree_format(*, file):
    """Validates a Newick tree by passing it through a parser"""
    file = Path(file).resolve()

    try:
        run_script_in_venv(
            venv_location=settings.COMPONENTS_VIRTUAL_ENV_BIOM_LOCATION,
            python_script=VALIDATION_SCRIPT_DIR / "validate_newick.py",
            args=[str(file)],
        )
    except subprocess.CalledProcessError as e:
        error_lines = e.stderr.strip().split("\n")
        for line in error_lines:
            # Pass along any validation errors
            if line.startswith("NewickValidationError"):
                error_message = line.split(":", 1)[1].strip()
                raise ValidationError(
                    error_message or "Does not appear to be a newick tree"
                )
        else:
            raise RuntimeError(f"An unexpected error occurred: {e.stderr}")


def validate_biom_format(*, file):
    """Validates an uploaded BIOM file by passing its content through a parser"""
    file = Path(file).resolve()

    try:
        run_script_in_venv(
            venv_location=settings.COMPONENTS_VIRTUAL_ENV_BIOM_LOCATION,
            python_script=VALIDATION_SCRIPT_DIR / "validate_biom.py",
            args=[str(file)],
        )
    except subprocess.CalledProcessError as e:
        error_lines = e.stderr.strip().split("\n")
        for line in error_lines:
            # Pass along any validation errors
            if line.startswith("BIOMValidationError"):
                error_message = line.split(":", 1)[1].strip()
                raise ValidationError(
                    error_message or "Does not appear to be a BIOM-format file"
                )
        else:
            raise RuntimeError(f"An unexpected error occurred: {e.stderr}")
