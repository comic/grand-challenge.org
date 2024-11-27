from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.components.validators import (
    validate_biom_format,
    validate_newick_tree_format,
    validate_safe_path,
)
from tests.components_tests import RESOURCE_DIR


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
    "biom_file, context, msg",
    (
        (
            # Working example
            RESOURCE_DIR / "biom" / "valid.biom",
            nullcontext(),
            None,
        ),
        (
            # Uncompressed
            RESOURCE_DIR / "biom" / "uncompressed_OTU_json.biom",
            pytest.raises(ValidationError),
            "Only BIOM in valid HDF5 binary file format are supported",
        ),
        (
            # Compressed, but removed first few bytes
            RESOURCE_DIR / "biom" / "broken.biom",
            pytest.raises(ValidationError),
            "Only BIOM in valid HDF5 binary file format are supported",
        ),
        (
            # HD5 Format, but not a biom
            RESOURCE_DIR / "biom" / "not_a_biom.h5",
            pytest.raises(ValidationError),
            "Does not appear to be a BIOM-format file",
        ),
    ),
)
def test_validate_biom_format(biom_file, context, msg):
    with context as c:
        validate_biom_format(file=biom_file)

    if msg:
        assert msg in str(c)
