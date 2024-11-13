from Bio import Phylo
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


def validate_newick_tree_format(tree):
    """Validates a Newick tree by passing it through a validator"""
    parser = Phylo.NewickIO.Parser.from_string(tree)

    try:
        has_tree = False
        for _ in parser.parse():
            has_tree = True
        if not has_tree:
            raise ValueError("No tree found")
    except Exception as e:
        raise ValidationError("Invalid Newick tree format:", e)
