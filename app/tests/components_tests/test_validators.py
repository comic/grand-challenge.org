from contextlib import nullcontext

import pytest
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from Bio.Phylo.NewickIO import NewickError
from django.core.exceptions import ValidationError
from requests import put

from grandchallenge.components.validators import (
    validate_biom_format,
    validate_newick_tree_format,
    validate_safe_path,
)
from tests.components_tests import RESOURCE_DIR
from tests.factories import UserFactory
from tests.uploads_tests.factories import UserUploadFactory


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


@pytest.mark.django_db
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
    creator = UserFactory()

    us = UserUploadFactory(filename="file.biom", creator=creator)
    presigned_urls = us.generate_presigned_urls(part_numbers=[1])
    with open(biom_file, "rb") as f:
        response = put(presigned_urls["1"], data=f)

    assert response.status_code == 200  # Sanity

    us.complete_multipart_upload(
        parts=[{"ETag": response.headers["ETag"], "PartNumber": 1}]
    )
    us.save()

    with context as c:
        validate_biom_format(user_upload=us)

    if msg:
        assert msg in str(c)


@pytest.mark.parametrize(
    "mocker_path, mock_error, expected_error, msg",
    (
        # Ensure all resource errors are covered
        (
            "grandchallenge.components.validators.h5py.File",
            MemoryError,
            ValidationError,
            "The file is too large",
        ),
        (
            "grandchallenge.components.validators.h5py.File",
            TimeLimitExceeded,
            ValidationError,
            "The file is too large",
        ),
        (
            "grandchallenge.components.validators.h5py.File",
            SoftTimeLimitExceeded,
            ValidationError,
            "The file is too large",
        ),
        # Ensure that it is also covered when parsing table
        (
            "grandchallenge.components.validators.biom.Table.from_hdf5",
            MemoryError,
            ValidationError,
            "The file is too large",
        ),
        # Other errors are caught as invalid BIOM
        (
            "grandchallenge.components.validators.biom.Table.from_hdf5",
            KeyError,
            ValidationError,
            "Does not appear to be a BIOM-format file",
        ),
    ),
)
def test_validate_biom_exception_handling(
    mocker_path, mock_error, msg, expected_error, mocker
):

    class MockUserUpload:
        @classmethod
        def download_fileobj(cls, fileobj):
            with open(RESOURCE_DIR / "biom" / "valid.biom", "rb") as f:
                fileobj.write(f.read())

    mocker.patch(mocker_path, side_effect=mock_error)

    with pytest.raises(expected_error) as err:
        validate_biom_format(user_upload=MockUserUpload)

    assert msg in str(err)
