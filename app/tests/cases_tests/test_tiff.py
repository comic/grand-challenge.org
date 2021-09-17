import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import tifffile as tiff_lib
from panimg.exceptions import ValidationError
from panimg.image_builders.tiff import (
    GrandChallengeTiffFile,
    _extract_tags,
    _get_color_space,
    _load_with_tiff,
    image_builder_tiff,
)
from panimg.models import ColorSpace
from panimg.panimg import _build_files
from pytest import approx
from tifffile import tifffile

from tests.cases_tests import RESOURCE_PATH


@pytest.mark.parametrize(
    "color_space_string, expected",
    [
        ("TEST.GRAY", ColorSpace.GRAY),
        ("TEST.MINISBLACK", ColorSpace.GRAY),
        ("TEST.minisblack", ColorSpace.GRAY),
        ("TEST.RGB", ColorSpace.RGB),
        ("TEST.RGBA", ColorSpace.RGBA),
        ("TEST.YCBCR", ColorSpace.YCBCR),
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
    (
        "path,"
        "color_space,"
        "resolution_levels,"
        "image_height,"
        "image_width,"
        "voxel_height_mm,"
        "voxel_width_mm,"
        "expected_error_message"
    ),
    [
        ("dummy.tiff", 1, 1, 10, 10, 0.1, 0.1, ""),
        (
            "dummy.tiff",
            1,
            None,
            10,
            10,
            0.1,
            0.1,
            "Not a valid tif: Resolution levels not valid",
        ),
        (
            "dummy.tiff",
            1,
            1,
            None,
            10,
            0.1,
            0.1,
            "Not a valid tif: Image height could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            None,
            0.1,
            0.1,
            "Not a valid tif: Image width could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            10,
            None,
            0.1,
            "Not a valid tif: Voxel height could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            10,
            0.1,
            None,
            "Not a valid tif: Voxel width could not be determined",
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
        gc_file = GrandChallengeTiffFile(Path(path))
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
    gc_file.pk = uuid4()
    try:
        _load_with_tiff(gc_file=gc_file)
    except ValidationError as e:
        error_message = str(e)

    assert expected_error_message in error_message
    if not expected_error_message:
        assert not error_message


@pytest.mark.parametrize(
    "source_dir, filename",
    [(RESOURCE_PATH, "valid_tiff.tif"), (RESOURCE_PATH, "no_dzi.tif")],
)
def test_load_with_open_slide(source_dir, filename, tmpdir_factory):
    # Copy resource file to writable temp folder
    temp_file = Path(tmpdir_factory.mktemp("temp") / filename)
    shutil.copy(source_dir / filename, temp_file)
    gc_file = GrandChallengeTiffFile(temp_file)
    output_dir = Path(tmpdir_factory.mktemp("output"))
    (output_dir / filename).mkdir()

    gc_file = _load_with_tiff(gc_file=gc_file)
    assert gc_file.validate() is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resource, expected_error_message, voxel_size",
    [(RESOURCE_PATH / "valid_tiff.tif", "", [1, 1])],
)
def test_tiff_image_entry_creation(
    resource, expected_error_message, voxel_size
):
    error_message = ""
    gc_file = GrandChallengeTiffFile(resource)
    try:
        tiff_file = tifffile.TiffFile(str(gc_file.path.absolute()))
        gc_file = _extract_tags(gc_file=gc_file, pages=tiff_file.pages)
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

        assert gc_file.path.name == resource.name
        assert gc_file.image_width == tiff_tags["ImageWidth"].value
        assert gc_file.image_height == tiff_tags["ImageLength"].value
        assert gc_file.resolution_levels == len(tiff_file.pages)
        assert gc_file.color_space == _get_color_space(
            color_space_string=str(
                tiff_tags["PhotometricInterpretation"].value
            )
        )
        assert gc_file.voxel_width_mm == approx(voxel_size[0])
        assert gc_file.voxel_height_mm == approx(voxel_size[1])


# Integration test of all features being accessed through the image builder
@pytest.mark.django_db
def test_image_builder_tiff(tmpdir_factory,):
    # Copy resource files to writable temp folder
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    output_dir = Path(tmpdir_factory.mktemp("output"))

    shutil.copytree(
        RESOURCE_PATH,
        temp_dir,
        ignore=shutil.ignore_patterns("dicom*", "complex_tiff", "dzi_tiff"),
    )
    files = [Path(d[0]).joinpath(f) for d in os.walk(temp_dir) for f in d[2]]

    image_builder_result = _build_files(
        builder=image_builder_tiff, files=files, output_directory=output_dir
    )

    expected_files = [
        temp_dir / "valid_tiff.tif",
        temp_dir / "no_dzi.tif",
    ]

    assert sorted(image_builder_result.consumed_files) == sorted(
        expected_files
    )

    file_to_pk = {i.name: i.pk for i in image_builder_result.new_images}

    for file in expected_files:
        pk = file_to_pk[file.name]
        assert os.path.isfile(output_dir / file.name / f"{pk}.tif")

    # Assert that both tiff images are imported
    assert len(image_builder_result.new_image_files) == 2


def test_error_handling(tmpdir_factory):
    # Copy resource files to writable temp folder
    # The content files are dummy files and won't compile to tiff.
    # The point is to test the loading of gc_files and make sure all
    # related files are associated with the gc_file
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    shutil.copytree(RESOURCE_PATH / "complex_tiff", temp_dir)
    files = {Path(d[0]).joinpath(f) for d in os.walk(temp_dir) for f in d[2]}

    with TemporaryDirectory() as output:
        image_builder_result = _build_files(
            builder=image_builder_tiff, files=files, output_directory=output
        )

    assert len(image_builder_result.file_errors) == 14
