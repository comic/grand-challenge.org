"""
Tests for the mhd-file reconstruction.
"""

import SimpleITK
import pytest
from pathlib import Path

from grandchallenge.cases.image_builders.metaio_utils import (
    load_sitk_image,
    load_sitk_image_with_nd_support_from_headers,
    parse_mh_header,
)
from tests.cases_tests import RESOURCE_PATH


def test_parse_header_valid_4d_mhd():
    headers = parse_mh_header(RESOURCE_PATH / "image10x11x12x13.mhd")
    assert headers == {
        "ObjectType": "Image",
        "NDims": "4",
        "BinaryData": "True",
        "BinaryDataByteOrderMSB": "False",
        "CompressedData": "True",
        "CompressedDataSize": "39",
        "TransformMatrix": "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1",
        "Offset": "-131 -99 -917 0",
        "CenterOfRotation": "0 0 0 0",
        "AnatomicalOrientation": "RAI",
        "ElementSpacing": "0.429 0.429 0.5 1",
        "DimSize": "10 11 12 13",
        "ElementType": "MET_UCHAR",
        "ElementDataFile": "image10x11x12x13.zraw",
    }


def test_parse_header_valid_mhd():
    headers = parse_mh_header(RESOURCE_PATH / "image10x10x10.mhd")
    assert headers == {
        "ObjectType": "Image",
        "NDims": "3",
        "BinaryData": "True",
        "BinaryDataByteOrderMSB": "False",
        "CompressedData": "True",
        "CompressedDataSize": "7551",
        "TransformMatrix": "1 0 0 0 1 0 0 0 1",
        "Offset": "0 0 0",
        "CenterOfRotation": "0 0 0",
        "AnatomicalOrientation": "RAI",
        "ElementSpacing": "1 1 1",
        "DimSize": "10 10 10",
        "ElementType": "MET_DOUBLE",
        "ElementDataFile": "image10x10x10.zraw",
    }


def test_parse_header_valid_mhd_with_extra_fields():
    headers = parse_mh_header(RESOURCE_PATH / "image10x10x10-extra-stuff.mhd")
    assert headers == {
        "ObjectType": "Image",
        "NDims": "3",
        "BinaryData": "True",
        "BinaryDataByteOrderMSB": "False",
        "CompressedData": "True",
        "CompressedDataSize": "7551",
        "TransformMatrix": "1 0 0 0 1 0 0 0 1",
        "Offset": "0 0 0",
        "CenterOfRotation": "0 0 0",
        "AnatomicalOrientation": "RAI",
        "ElementSpacing": "1 1 1",
        "DimSize": "10 10 10",
        "ElementType": "MET_DOUBLE",
        "ElementDataFile": "image10x10x10.zraw",
        "# Extra stuff": None,
        "woohoo": None,
        "Some_values": '"Huh? \u2713\U0001f604"',
    }


def assert_sitk_img_equivalence(
    img: SimpleITK.Image, img_ref: SimpleITK.Image
):
    assert img.GetDimension() == img_ref.GetDimension()
    assert img.GetSize() == img_ref.GetSize()
    assert img.GetOrigin() == img_ref.GetOrigin()
    assert img.GetSpacing() == img_ref.GetSpacing()
    assert (
        img.GetNumberOfComponentsPerPixel()
        == img_ref.GetNumberOfComponentsPerPixel()
    )
    assert img.GetPixelIDValue() == img_ref.GetPixelIDValue()
    assert img.GetPixelIDTypeAsString() == img_ref.GetPixelIDTypeAsString()


def test_writing_4d_mhd_produces_same_results(tmpdir):
    def assert_img_properties(img: SimpleITK.Image):
        assert img.GetDimension() == 4
        assert img.GetWidth() == 10
        assert img.GetHeight() == 11
        assert img.GetDepth() == 12
        assert img.GetSize()[-1] == 13

    img_ref = load_sitk_image(RESOURCE_PATH / "image10x11x12x13.mhd")
    assert_img_properties(img_ref)
    copypath = Path(tmpdir / "temp4d.mhd")
    SimpleITK.WriteImage(img_ref, str(copypath), True)
    img = load_sitk_image(copypath)
    assert_img_properties(img)
    assert_sitk_img_equivalence(img, img_ref)


@pytest.mark.parametrize(
    "image",
    (
        RESOURCE_PATH / "image3x4.mhd",
        RESOURCE_PATH / "image5x6x7.mhd",
        RESOURCE_PATH / "image128x256x4RGB.mhd",
        RESOURCE_PATH / "image10x10x10-extra-stuff.mhd",
    ),
)
def test_4dloader_reproduces_normal_sitk_loader_results(image: Path):
    img_ref = SimpleITK.ReadImage(str(image))
    headers = parse_mh_header(image)
    data_file_path = (
        image.resolve().parent / Path(headers["ElementDataFile"]).name
    )
    img = load_sitk_image_with_nd_support_from_headers(
        headers=headers, data_file_path=data_file_path
    )
    assert_sitk_img_equivalence(img, img_ref)


def test_fail_on_invalid_utf8():
    with pytest.raises(ValueError):
        parse_mh_header(RESOURCE_PATH / "invalid_utf8.mhd")


def test_too_many_headers_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        for i in range(1000000):
            f.write(f"key{i} = {i}\n")

    with pytest.raises(ValueError):
        parse_mh_header(test_file_path)


def test_line_too_long(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("key = ")
        for i in range(1000000):
            f.write(f"{i}")

    with pytest.raises(ValueError):
        parse_mh_header(test_file_path)


def test_does_not_choke_on_empty_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("\n")

    assert parse_mh_header(test_file_path) == {}
