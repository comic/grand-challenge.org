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


def _newick_parser(tree):
    return NewickIO.Parser.from_string(tree)


def validate_newick_tree_format(tree):
    """Validates a Newick tree by passing it through a parser"""
    parser = _newick_parser(tree)

    has_tree = False

    try:
        for _ in parser.parse():
            has_tree = True
    except (MemoryError, SoftTimeLimitExceeded, TimeLimitExceeded):
        raise ValidationError("The file is too large")
    except NewickIO.NewickError as e:
        raise ValidationError(f"Invalid Newick tree format: {e}")

    if not has_tree:
        raise ValidationError("No Newick tree found")
