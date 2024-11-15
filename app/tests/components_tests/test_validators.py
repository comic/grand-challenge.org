from contextlib import nullcontext

import pytest
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from Bio.Phylo.NewickIO import NewickError
from django.core.exceptions import ValidationError

from grandchallenge.components.validators import (
    validate_newick_tree_format,
    validate_safe_path,
)


@pytest.mark.parametrize(
    "rel_path",
    ["bar/../foo", "./foo", "../bar", "/sfdadfs", "////sfda", "foo/"],
)
def test_invalid_paths(rel_path):
    with pytest.raises(ValidationError):
        validate_safe_path(rel_path)


@pytest.mark.parametrize(
    "rel_path", ["foo", "foo/bar", "foo/bar.tar.gz", "foo/{{ filename }}.zip"]
)
def test_valid_paths(rel_path):
    validate_safe_path(rel_path)


@pytest.mark.parametrize(
    "tree, context",
    (
        (
            "();",  # Empty tree
            nullcontext(),
        ),
        (
            "()",  # Empty tree
            nullcontext(),
        ),
        (
            "((A,B),C);",
            nullcontext(),
        ),
        (
            "((A,B),C);\n((D,E),F);",  # Multiple trees are OK.
            nullcontext(),
        ),
        (
            "((,),);",  # Sanity, no labels
            nullcontext(),
        ),
        (
            "(中,(国,话));",  # utf-8 checks
            nullcontext(),
        ),
        (
            "",  # Empty
            pytest.raises(ValidationError),
        ),
        (
            "((A,B),C;",  # Unbalanced Paranthesis, clearly wrong format
            pytest.raises(ValidationError),
        ),
        (
            "((A@B),C;",  # Unexpected characters
            pytest.raises(ValidationError),
        ),
    ),
)
def test_validate_newick_formats(tree, context):
    with context:
        validate_newick_tree_format(tree=tree)


@pytest.mark.parametrize(
    "error, msg, expected_error",
    (
        (MemoryError, "The file is too large", ValidationError),
        (SoftTimeLimitExceeded, "The file is too large", ValidationError),
        (TimeLimitExceeded, "The file is too large", ValidationError),
        (NewickError, "Invalid Newick tree format", ValidationError),
        (  # No secrets: only ValidationErrors are returned to user
            Exception,
            "",
            Exception,
        ),
    ),
)
def test_validate_newick_exception_handling(
    error, msg, expected_error, mocker
):

    class MockParser:
        @staticmethod
        def parse(*_, **__):
            raise error

    mocker.patch(
        "grandchallenge.components.validators._newick_parser",
        return_value=MockParser,
    )

    with pytest.raises(expected_error) as err:
        validate_newick_tree_format("();")

    assert msg in str(err)
