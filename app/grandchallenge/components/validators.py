from functools import wraps
from io import BytesIO

import biom
import h5py
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from Bio.Phylo import NewickIO
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


def _handle_validation_resource_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except (MemoryError, SoftTimeLimitExceeded, TimeLimitExceeded):
            raise ValidationError("The file is too large")

    return wrapper


def _newick_parser(tree):
    return NewickIO.Parser.from_string(tree)


@_handle_validation_resource_errors
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


@_handle_validation_resource_errors
def validate_biom_format(*, user_upload):
    """Validates an uploaded BIOM file by passing its content through a parser"""

    with BytesIO() as fileobj:
        # Get the object into memory
        user_upload.download_fileobj(fileobj)
        fileobj.seek(0)

        # Attempt to wrap it in a hdf5 handler
        try:
            hdf5_file = h5py.File(fileobj, "r")
        except OSError:
            raise ValidationError(
                "Only BIOM in valid HDF5 binary file format are supported"
            )

        # Attempt to parse it as a BIOM table
        try:
            _handle_validation_resource_errors(biom.Table.from_hdf5)(hdf5_file)
        except ValidationError as e:
            raise e
        except Exception:
            raise ValidationError("Does not appear to be a BIOM-format file")
