import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
import tifffile as tiff_lib
from django.core.exceptions import ValidationError
from pytest import approx
from tifffile import tifffile

from grandchallenge.cases.image_builders.tiff import (
    GrandChallengeTiffFile,
    _create_dzi_images,
    _create_tiff_image_entry,
    _extract_tags,
    _get_color_space,
    _load_with_open_slide,
    _load_with_tiff,
    image_builder_tiff,
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
        color_space = _get_color_space(color_space_string=color_space_string)
    except ValidationError:
        pass

    assert color_space is expected


@pytest.mark.parametrize(
    "path, color_space, resolution_levels, image_height, image_width, voxel_height_mm, voxel_width_mm, expected_error_message",
    [
        ("dummy.tiff", 1, 1, 10, 10, 0.1, 0.1, ""),
        ("dummy.tiff", None, 1, 10, 10, 0.1, 0.1, "ColorSpace not valid"),
        (
            "dummy.tiff",
            1,
            None,
            10,
            10,
            0.1,
            0.1,
            "Resolution levels not valid",
        ),
        (
            "dummy.tiff",
            1,
            1,
            None,
            10,
            0.1,
            0.1,
            "ImageHeigth could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            None,
            0.1,
            0.1,
            "ImageWidth could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            10,
            None,
            0.1,
            "Voxel height could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            10,
            0.1,
            None,
            "Voxel width could not be determined",
        ),
    ],
)
def test_grandchallengetifffile_validation(
    path,
    color_space,
    resolution_levels,
    image_height,
    image_width,
    voxel_height_mm,
    voxel_width_mm,
    expected_error_message,
):
    error_message = ""

    try:
        gc_file = GrandChallengeTiffFile(path)
        gc_file.color_space = color_space
        gc_file.resolution_levels = resolution_levels
        gc_file.image_height = image_height
        gc_file.image_width = image_width
        gc_file.voxel_height_mm = voxel_height_mm
        gc_file.voxel_width_mm = voxel_width_mm
        gc_file.validate()
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.parametrize(
    "source_dir, filename, expected_error_message",
    [
        (RESOURCE_PATH, "valid_tiff.tif", ""),
        (
            RESOURCE_PATH,
            "invalid_resolutions_tiff.tif",
            "Invalid resolution unit RESUNIT.NONE in tiff file",
        ),
    ],
)
def test_load_with_tiff(
    source_dir, filename, expected_error_message, tmpdir_factory
):
    error_message = ""
    # Copy resource file to writable temp folder
    temp_file = Path(tmpdir_factory.mktemp("temp") / filename)
    shutil.copy(source_dir / filename, temp_file)
    gc_file = GrandChallengeTiffFile(temp_file)
    try:
        _load_with_tiff(gc_file=gc_file)
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.parametrize(
    "source_dir, filename, expected_error_message",
    [
        (RESOURCE_PATH, "valid_tiff.tif", ""),
        (
            RESOURCE_PATH,
            "no_dzi.tif",
            "Image can't be converted to dzi: unable to call dzsave",
        ),
    ],
)
def test_load_with_open_slide(
    source_dir, filename, expected_error_message, tmpdir_factory
):
    error_message = ""
    # Copy resource file to writable temp folder
    temp_file = Path(tmpdir_factory.mktemp("temp") / filename)
    shutil.copy(source_dir / filename, temp_file)
    gc_file = GrandChallengeTiffFile(temp_file)
    pk = uuid4()
    try:
        _, gc_file = _load_with_tiff(gc_file=gc_file)
        _load_with_open_slide(gc_file=gc_file, pk=pk)
    except Exception as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.parametrize(
    "source_dir, filename, expected_error_message",
    [
        (RESOURCE_PATH, "valid_tiff.tif", ""),
        (
            RESOURCE_PATH,
            "no_dzi.tif",
            "Image can't be converted to dzi: unable to call dzsave",
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
    gc_file = GrandChallengeTiffFile(temp_file)
    pk = uuid4()
    try:
        _create_dzi_images(gc_file=gc_file, pk=pk)
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource, expected_error_message, voxel_size",
    [(RESOURCE_PATH / "valid_tiff.tif", "", [1, 1, None])],
)
def test_tiff_image_entry_creation(
    resource, expected_error_message, voxel_size
):
    error_message = ""
    image_entry = None
    pk = uuid4()
    gc_file = GrandChallengeTiffFile(resource)
    try:
        tiff_file = tifffile.TiffFile(str(gc_file.path.absolute()))
        gc_file = _extract_tags(gc_file=gc_file, pages=tiff_file.pages)
        image_entry = _create_tiff_image_entry(tiff_file=gc_file, pk=pk)
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
        assert image_entry.color_space == _get_color_space(
            color_space_string=str(
                tiff_tags["PhotometricInterpretation"].value
            )
        )
        assert image_entry.voxel_width_mm == approx(voxel_size[0])
        assert image_entry.voxel_height_mm == approx(voxel_size[1])
        assert image_entry.voxel_depth_mm == voxel_size[2]
        assert image_entry.pk == pk


# Integration test of all features being accessed through the image builder
@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource, expected_files, expected_image_files, expected_dzi_files",
    [(RESOURCE_PATH, 4, 7, 31)],
)
def test_image_builder_tiff(
    resource,
    expected_files,
    expected_image_files,
    expected_dzi_files,
    tmpdir_factory,
):
    # Copy resource files to writable temp folder
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    shutil.copytree(
        resource, temp_dir, ignore=shutil.ignore_patterns("dicom*"),
    )

    image_builder_result = image_builder_tiff(path=temp_dir)

    assert len(image_builder_result.consumed_files) == expected_files
    assert len(image_builder_result.new_images) == expected_files
    assert len(image_builder_result.new_image_files) == expected_image_files

    # Asserts successful creation of files
    new_image_pk = image_builder_result.new_images[0].pk
    assert os.path.isfile(temp_dir / f"{new_image_pk}.dzi")
    assert os.path.isdir(temp_dir / f"{new_image_pk}_files")

    assert len(list(temp_dir.glob("**/*.jpeg"))) == expected_dzi_files
