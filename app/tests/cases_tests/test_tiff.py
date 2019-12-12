import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
import tifffile as tiff_lib
from django.core.exceptions import ValidationError
from pytest import approx

from grandchallenge.cases.image_builders.tiff import (
    create_dzi_images,
    create_tiff_image_entry,
    get_color_space,
    image_builder_tiff,
    load_tiff_file,
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
    except ValidationError:
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
            "Tiff file is missing required tag TileOffsets",
        ),
    ],
)
def test_tiff_validation(resource, expected_error_message):
    error_message = ""

    try:
        load_tiff_file(path=resource)
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.parametrize(
    "source_dir, filename, expected_error_message",
    [
        (RESOURCE_PATH, "valid_tiff.tif", ""),
        (RESOURCE_PATH, "image5x6x7.mhd", "Image isn't a TIFF file"),
        (
            RESOURCE_PATH,
            "invalid_meta_data_tiff.tif",
            "Image contains unauthorized information",
        ),
        (
            RESOURCE_PATH,
            "invalid_resolutions_tiff.tif",
            "Image only has a single resolution level",
        ),
        (
            RESOURCE_PATH,
            "invalid_tiles_tiff.tif",
            "Tiff file is missing required tag TileOffsets",
        ),
    ],
)
def test_dzi_creation(
    source_dir, filename, expected_error_message, tmpdir_factory
):
    error_message = ""
    # Copy resource file to writable temp folder
    temp_file = Path(tmpdir_factory.mktemp("temp") / filename)
    shutil.copy(source_dir / filename, temp_file)

    try:
        # Load the tiff file and create dzi
        tiff_file = load_tiff_file(path=temp_file)
        create_dzi_images(tiff_file=tiff_file, pk=uuid4())
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource, expected_error_message, voxel_size",
    [
        (RESOURCE_PATH / "valid_tiff.tif", "", [1, 1, None],),
        (
            RESOURCE_PATH / "image5x6x7.mhd",
            "Image isn't a TIFF file",
            [0, 0, 0],
        ),
    ],
)
def test_tiff_image_entry_creation(
    resource, expected_error_message, voxel_size
):
    error_message = ""
    image_entry = None
    pk = uuid4()
    try:
        tiff_file = load_tiff_file(path=resource)
        image_entry = create_tiff_image_entry(tiff_file=tiff_file, pk=pk)
    except ValidationError as e:
        error_message = str(e)

    # Asserts possible file opening failures
    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message

    # Asserts successful creation data
    if not expected_error_message:
        tiff_file = tiff_lib.TiffFile(str(resource.absolute()))
        tiff_tags = tiff_file.pages[0].tags

        assert image_entry.name == resource.name
        assert image_entry.width == tiff_tags["ImageWidth"].value
        assert image_entry.height == tiff_tags["ImageLength"].value
        assert image_entry.depth == 1
        assert image_entry.resolution_levels == len(tiff_file.pages)
        assert image_entry.color_space == get_color_space(
            str(tiff_tags["PhotometricInterpretation"].value)
        )
        assert image_entry.voxel_width_mm == approx(voxel_size[0])
        assert image_entry.voxel_height_mm == approx(voxel_size[1])
        assert image_entry.voxel_depth_mm == voxel_size[2]
        assert image_entry.pk == pk


# Integration test of all features being accessed through the image builder
@pytest.mark.django_db
def test_image_builder_tiff(tmpdir_factory):
    # Copy resource files to writable temp folder
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    shutil.copytree(
        RESOURCE_PATH, temp_dir, ignore=shutil.ignore_patterns("dicom")
    )

    image_builder_result = image_builder_tiff(temp_dir)

    # Assumes the RESOURCE_PATH folder only contains a single correct TIFF file
    assert len(image_builder_result.consumed_files) == 1
    assert len(image_builder_result.new_images) == 1
    assert len(image_builder_result.new_image_files) == 2

    # Asserts successful creation of files
    new_image_pk = image_builder_result.new_images[0].pk
    assert os.path.isfile(temp_dir / f"{new_image_pk}.dzi")
    assert os.path.isdir(temp_dir / f"{new_image_pk}_files")

    assert len(list(temp_dir.glob("**/*.jpeg"))) == 9
