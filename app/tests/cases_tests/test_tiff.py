"""
Tests for the TIFF-file validation.
"""

import pytest
import tifffile as tiff_lib
from django.core.exceptions import ValidationError
from grandchallenge.cases.image_builders.tiff import (
    image_builder_tiff,
    validate_tiff,
    create_tiff_image_entry,
    get_color_space,
)
from grandchallenge.cases.models import Image
from tests.cases_tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "color_space_string, expected",
    [
        ("TEST.GRAY", Image.COLOR_SPACE_GRAY),
        ("TEST.MINISBLACK", Image.COLOR_SPACE_GRAY),
        ("TEST.minisblack", Image.COLOR_SPACE_GRAY),
        ("TEST.RGB", Image.COLOR_SPACE_RGB),
        ("TEST.RGBA", Image.COLOR_SPACE_RGBA),
        ("TEST.YCBCR", Image.COLOR_SPACE_YCBCR),
        ("Not.Colour", None),
    ],
)
def test_get_color_space(color_space_string, expected):
    color_space = None

    try:
        color_space = get_color_space(color_space_string)
    except ValueError:
        pass

    assert color_space is expected


@pytest.mark.parametrize(
    "resource, expected_error_message",
    [
        (RESOURCE_PATH / "valid_tiff.tif", ""),
        (RESOURCE_PATH / "image5x6x7.mhd", "Image isn't a TIFF file"),
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource, expected_error_message",
    [
        (RESOURCE_PATH / "valid_tiff.tif", ""),
        (RESOURCE_PATH / "image5x6x7.mhd", "Image isn't a TIFF file"),
    ],
)
def test_tiff_image_entry_creation(resource, expected_error_message):
    error_message = ""

    try:
        image_entry = create_tiff_image_entry(resource)
    except ValidationError as e:
        error_message = e.message

    # Asserts possible file opening failures
    assert error_message == expected_error_message

    # Asserts succesful creation data
    try:
        tiff_file = tiff_lib.TiffFile(str(resource.absolute()))
        tiff_tags = tiff_file.pages[0].tags

        assert image_entry.name == resource.name
        assert image_entry.width == tiff_tags["ImageWidth"].value
        assert image_entry.height == tiff_tags["ImageLength"].value
        assert image_entry.depth is None
        assert image_entry.resolution_levels == len(tiff_file.pages)
        assert image_entry.color_space == get_color_space(
            str(tiff_tags["PhotometricInterpretation"].value)
        )

    except ValueError:
        pass


# Integration test of all features being accessed through the image builder
@pytest.mark.django_db
def test_image_builder_tiff():
    image_builder_result = image_builder_tiff(RESOURCE_PATH)

    # Assumes the RESOURCE_PATH folder only contains a single correct TIFF file
    assert len(image_builder_result.consumed_files) == 1
    assert len(image_builder_result.new_images) == 1
    assert len(image_builder_result.new_image_files) == 1
