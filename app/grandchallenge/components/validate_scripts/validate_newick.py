"""
Script that validates newick trees by passing them through a parser.
Provide the newick tree file as an argument to the script.

If the file is valid, the script will exit cleanly (0).
Raises a NewickValidationError if the newick tree file is not valid.



The rational for having a seperate script and virtual environment is to provide
isolation of web-app and modality-specific libraries.
"""

import sys
from pathlib import Path

from Bio.Phylo import NewickIO  # noqa: F821


class NewickValidationError(Exception):
    pass


def run(file_path):
    with file_path.open("r") as f:
        tree = f.read()

    parser = NewickIO.Parser.from_string(tree)

    has_tree = False

    try:
        for _ in parser.parse():
            has_tree = True
    except NewickIO.NewickError as e:
        raise NewickValidationError(f"Invalid Newick tree format: {e}")

    if not has_tree:
        raise NewickValidationError("No Newick tree found")


def _get_file_path():
    if len(sys.argv) == 2:
        file_path = Path(sys.argv[1])
        if not file_path.is_file():
            raise RuntimeError(
                f"Provided newick tree file path is not an existing file: {file_path}"
            )
        return file_path
    else:
        raise RuntimeError(
            "Incorrect number of arguments, provide (only) the newick tree file path"
        )


if __name__ == "__main__":
    run(_get_file_path())
