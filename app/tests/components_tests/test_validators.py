from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.components.validators import (
    validate_newick,
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
            "((A,B),C);((D,E),F);",  # Multiple trees are OK.
            nullcontext(),
        ),
        (
            "((,),);",
            nullcontext(),
        ),
        (
            "",  # Empty
            pytest.raises(ValidationError),
        ),
        (
            "((A,B),C;",  # Unbalanced Paranthesis
            pytest.raises(ValidationError),
        ),
        (
            "((A@B),C;",  # Unexpected characters
            pytest.raises(ValidationError),
        ),
        (
            "(:0.5,A:0.3);",  # Branch lengths without a node
            pytest.raises(ValidationError),
        ),
        (
            "(A,B,);",  # Missing Node
            pytest.raises(ValidationError),
        ),
        (
            "(A,A);",  # Duplicate  labels
            pytest.raises(ValidationError),
        ),
    ),
)
def test_validate_newick(tree, context):
    with context:
        validate_newick(tree=tree)
