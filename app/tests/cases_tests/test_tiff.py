"""
Tests for the TIFF-file validation.
"""

import pytest
from tests.cases_tests import RESOURCE_PATH
from grandchallenge.cases.image_builders.tiff import validate_tiff


def test_parse_valid_tiff():
    valid, message = validate_tiff(RESOURCE_PATH / "valid_tiff.tif")
    assert valid


def test_parse_invalid_meta_data_tiff():
    valid, message = validate_tiff(
        RESOURCE_PATH / "invalid_meta_data_tiff.tif"
    )
    invalid = not valid

    assert invalid
    assert message == "Image contains unauthorized information"


def test_parse_invalid_single_resolution_tiff():
    valid, message = validate_tiff(
        RESOURCE_PATH / "invalid_resolutions_tiff.tif"
    )
    invalid = not valid

    assert message == "Image only has a single resolution level"
    assert invalid


def test_parse_invalid_tile_information_tiff():
    valid, message = validate_tiff(RESOURCE_PATH / "invalid_tiles_tiff.tif")
    invalid = not valid

    assert message == "Image has incomplete tile information"
    assert invalid
