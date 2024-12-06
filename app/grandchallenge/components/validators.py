import subprocess
from pathlib import Path

from Bio.Phylo import NewickIO
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


def _newick_parser(tree):
    return NewickIO.Parser.from_string(tree)


def validate_newick_tree_format(tree):
    """Validates a Newick tree by passing it through a parser"""
    parser = _newick_parser(tree)

    has_tree = False

    try:
        for _ in parser.parse():
            has_tree = True
    except NewickIO.NewickError as e:
        raise ValidationError(f"Invalid Newick tree format: {e}")

    if not has_tree:
        raise ValidationError("No Newick tree found")


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
            if line.startswith("ValidationScriptError"):
                error_message = line.split(":", 1)[1].strip()
                raise ValidationError(
                    error_message or "Does not appear to be a BIOM-format file"
                )
        else:
            raise RuntimeError(f"An unexpected error occured: {e.stderr}")
