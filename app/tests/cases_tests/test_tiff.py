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
    _convert_to_tiff,
    _create_dzi_images,
    _create_tiff_image_entry,
    _extract_tags,
    _get_color_space,
    _load_and_create_dzi,
    _load_gc_files,
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
            "Not a valid tif: ImageHeigth could not be determined",
        ),
        (
            "dummy.tiff",
            1,
            1,
            10,
            None,
            0.1,
            0.1,
            "Not a valid tif: ImageWidth could not be determined",
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
    try:
        gc_file = _load_with_tiff(gc_file=gc_file)
        _load_and_create_dzi(gc_file=gc_file)
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
    try:
        _create_dzi_images(gc_file=gc_file)
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
    gc_file = GrandChallengeTiffFile(resource)
    try:
        tiff_file = tifffile.TiffFile(str(gc_file.path.absolute()))
        gc_file = _extract_tags(gc_file=gc_file, pages=tiff_file.pages)
        image_entry = _create_tiff_image_entry(tiff_file=gc_file)
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
        assert image_entry.pk == gc_file.pk


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


@pytest.mark.skip(
    reason="skip for now as we don't want to upload a large testset"
)
@pytest.mark.parametrize(
    "resource, filelist",
    [
        (
            RESOURCE_PATH / "complex_tiff",
            [
                "0-CMU-1-Saved-1_16/Index.dat",
                "0-CMU-1-Saved-1_16/Slidedat.ini",
                "0-CMU-1-Saved-1_16/Data0000.dat",
                "0-CMU-1-Saved-1_16/Data0001.dat",
                "0-CMU-1-Saved-1_16/Data0002.dat",
                "0-CMU-1-Saved-1_16/Data0003.dat",
                "0-CMU-1-Saved-1_16/Data0004.dat",
                "0-CMU-1-Saved-1_16/Data0005.dat",
                "0-CMU-1-Saved-1_16/Data0006.dat",
                "0-CMU-1-Saved-1_16/Data0007.dat",
                "0-CMU-1-Saved-1_16/Data0008.dat",
                "0-CMU-1-Saved-1_16/Data0009.dat",
                "0-CMU-1-Saved-1_16/Data0010.dat",
                "0-CMU-1-Saved-1_16/Data0011.dat",
                "0-CMU-1-Saved-1_16/Data0012.dat",
                "0-CMU-1-Saved-1_16/Data0013.dat",
                "0-CMU-1-Saved-1_16/Data0014.dat",
                "0-CMU-1-Saved-1_16/Data0015.dat",
                "0-CMU-1-Saved-1_16/Data0016.dat",
                "0-CMU-1-Saved-1_16/Data0017.dat",
                "0-CMU-1-Saved-1_16/Data0018.dat",
                "CMU-1-40x - 2010-01-12 13.24.05.jpg",
                "CMU-1-40x - 2010-01-12 13.24.05(1,0).jpg",
                "CMU-1-40x - 2010-01-12 13.24.05(0,1).jpg",
                "CMU-1-40x - 2010-01-12 13.24.05(1,1).jpg",
                "CMU-1-40x - 2010-01-12 13.24.05_map2.jpg",
                "CMU-1-40x - 2010-01-12 13.24.05.opt",
                "CMU-1-40x - 2010-01-12 13.24.05_macro.jpg",
            ],
        ),
    ],
)
def test_handle_complex_files(resource, filelist, tmpdir_factory):
    # Copy resource files to writable temp folder
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    shutil.copytree(resource, temp_dir)
    gc_list = _load_gc_files(path=temp_dir)
    assert len(gc_list) == 2
    for file in filelist:
        assert os.path.isfile(temp_dir / file)


@pytest.mark.skip(
    reason="skip for now as we don't want to upload a large testset"
)
@pytest.mark.parametrize(
    "resource, filename",
    [
        (
            RESOURCE_PATH / "convert_to_tiff" / "Hamamatsu-VMS",
            "0-Test-CMU-1-40x - 2010-01-12 13.24.05.vms",
        ),
        (RESOURCE_PATH / "convert_to_tiff", "Aperio JP2K-33003-1.svs"),
        (RESOURCE_PATH / "convert_to_tiff", "Hamamatsu CMU-1.ndpi"),
        (RESOURCE_PATH / "convert_to_tiff", "Leica-1.scn"),
        (RESOURCE_PATH / "convert_to_tiff", "Mirax2-Fluorescence-1.mrxs"),
        (RESOURCE_PATH / "convert_to_tiff", "Ventana OS-1.bif",),
    ],
)
def test_convert_to_tiff(resource, filename, tmpdir_factory):
    pk = uuid4()
    temp_dir = Path(tmpdir_factory.mktemp("temp") / "resources")
    shutil.copytree(resource, temp_dir)
    tiff_file = _convert_to_tiff(path=resource / filename, pk=pk)
    assert tiff_file is not None
