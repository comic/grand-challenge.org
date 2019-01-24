"""
Tests for the TIFF-file validation.
"""

import pytest
from django.core.exceptions import ValidationError
from grandchallenge.cases.image_builders.tiff import validate_tiff
from tests.cases_tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "resource, expected_error_message",
    [
        (RESOURCE_PATH / "valid_tiff.tif", ""),
        (
            RESOURCE_PATH / "invalid_meta_data_tiff.tif",
            "Image contains unauthorized information",
        ),
        (
            RESOURCE_PATH / "invalid_resolutions_tiff.tif",
            "Image only has a single resolution level",
        ),
        (
            RESOURCE_PATH / "invalid_tiles_tiff.tif",
            "Image has incomplete tile information",
        ),
    ],
)
def test_tiff_validation(resource, expected_error_message):
    error_message = ""

    try:
        validate_tiff(resource)
    except ValidationError as e:
        error_message = e.message

    assert error_message == expected_error_message
