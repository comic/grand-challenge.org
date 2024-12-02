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
def test_validate_newick_format(tree, context):
    with context:
        validate_newick_tree_format(tree=tree)


def test_valid_biom_format():
    validate_biom_format(file=RESOURCE_DIR / "biom" / "valid.biom")


@pytest.mark.parametrize(
    "biom_file, msg",
    (
        (
            # Uncompressed
            RESOURCE_DIR / "biom" / "uncompressed_OTU_json.biom",
            "Only BIOM in valid HDF5 binary file format are supported",
        ),
        (
            # Compressed, but removed first few bytes
            RESOURCE_DIR / "biom" / "broken.biom",
            "Only BIOM in valid HDF5 binary file format are supported",
        ),
        (
            # HD5 Format, but not a biom
            RESOURCE_DIR / "biom" / "not_a_biom.h5",
            "Does not appear to be a BIOM-format file",
        ),
    ),
)
def test_invalid_biom_formats(biom_file, msg):
    with pytest.raises(ValidationError) as error:
        validate_biom_format(file=biom_file)
    assert msg in str(error)
