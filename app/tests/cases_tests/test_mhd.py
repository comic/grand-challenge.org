import shutil
import zlib
from pathlib import Path
from typing import List, Union

import SimpleITK
import pytest
from panimg.exceptions import ValidationError
from panimg.image_builders.metaio_utils import (
    ADDITIONAL_HEADERS,
    FLOAT_OR_FLOAT_ARRAY_MATCH_REGEX,
    load_sitk_image,
    parse_mh_header,
)

from tests.cases_tests import RESOURCE_PATH

MHD_WINDOW_DIR = RESOURCE_PATH / "mhd_window"


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
        "Some_values": '"Huh? \u2713\U0001f604"',
    }


def assert_sitk_img_equivalence(
    img: SimpleITK.Image, img_ref: SimpleITK.Image
):
    assert img.GetDimension() == img_ref.GetDimension()
    assert img.GetDirection() == img.GetDirection()
    assert img.GetSize() == img_ref.GetSize()
    assert img.GetOrigin() == img_ref.GetOrigin()
    assert img.GetSpacing() == img_ref.GetSpacing()
    assert (
        img.GetNumberOfComponentsPerPixel()
        == img_ref.GetNumberOfComponentsPerPixel()
    )
    assert img.GetPixelIDValue() == img_ref.GetPixelIDValue()
    assert img.GetPixelIDTypeAsString() == img_ref.GetPixelIDTypeAsString()


@pytest.mark.parametrize(
    "image",
    (
        RESOURCE_PATH / "image10x11x12x13.mhd",
        RESOURCE_PATH / "image10x11x12x13.mha",
    ),
)
def test_writing_4d_mhd_produces_same_results(tmpdir, image: Path):
    def assert_img_properties(img: SimpleITK.Image):
        assert img.GetDimension() == 4
        assert img.GetWidth() == 10
        assert img.GetHeight() == 11
        assert img.GetDepth() == 12
        assert img.GetSize()[-1] == 13

    img_ref = load_sitk_image(image)
    assert_img_properties(img_ref)
    copypath = Path(tmpdir / "temp4d.mhd")
    SimpleITK.WriteImage(img_ref, str(copypath), True)
    img = load_sitk_image(copypath)
    assert_img_properties(img)
    assert_sitk_img_equivalence(img, img_ref)


def test_4d_mh_loader_without_datafile_fails(tmpdir):
    src = RESOURCE_PATH / "image10x11x12x13.mhd"
    dest = Path(tmpdir) / src.name
    shutil.copy(str(src), str(dest))
    with pytest.raises(RuntimeError, match="File cannot be read"):
        load_sitk_image(dest)


def test_4d_mh_loader_with_invalid_data_type_fails(tmpdir):
    sources = [
        RESOURCE_PATH / "image10x11x12x13.mhd",
        RESOURCE_PATH / "image10x11x12x13.zraw",
    ]
    targets = []
    for src in sources:
        dest = Path(tmpdir) / src.name
        targets.append(dest)
        shutil.copy(str(src), str(dest))
    tmp_header_file = targets[0]
    with open(str(tmp_header_file)) as f:
        modified_header = f.read().replace("MET_UCHAR", "MET_OTHER")
    with open(str(tmp_header_file), "w") as f:
        f.write(modified_header)
    with pytest.raises(RuntimeError, match="Unknown PixelType"):
        load_sitk_image(tmp_header_file)


def test_4d_mh_loader_with_uncompressed_data(tmpdir):
    sources = [
        RESOURCE_PATH / "image10x11x12x13.mhd",
        RESOURCE_PATH / "image10x11x12x13.zraw",
    ]
    targets = []
    for src in sources:
        dest = Path(tmpdir) / src.name
        targets.append(dest)
        shutil.copy(str(src), str(dest))
    tmp_header_file, tmp_data_file = targets
    with open(str(tmp_header_file)) as f:
        modified_header = f.read().replace(
            "CompressedData = True", "CompressedData = False"
        )
    with open(str(tmp_header_file), "w") as f:
        f.write(modified_header)
    with open(str(tmp_data_file), "rb") as f:
        data = zlib.decompress(f.read())
    with open(str(tmp_data_file), "wb") as f:
        f.write(data)
    load_sitk_image(tmp_header_file)


def test_4d_mh_loader_with_more_than_4_dimensions_fails(tmpdir):
    src = RESOURCE_PATH / "image10x11x12x13.mhd"
    dest = Path(tmpdir) / src.name
    shutil.copy(str(src), str(dest))
    with open(str(dest)) as f:
        modified_header = f.read().replace("NDims = 4", "NDims = 5")
    with open(str(dest), "w") as f:
        f.write(modified_header)
    with pytest.raises(NotImplementedError):
        load_sitk_image(dest)


@pytest.mark.parametrize(
    "test_img",
    ["image10x11x12x13-extra-stuff.mhd", "image3x4-extra-stuff.mhd"],
)
def test_load_sitk_image_with_additional_meta_data(tmpdir, test_img: str):
    src = RESOURCE_PATH / test_img
    sitk_image = load_sitk_image(src)
    for key in sitk_image.GetMetaDataKeys():
        assert key in ADDITIONAL_HEADERS
        assert ADDITIONAL_HEADERS[key].match(sitk_image.GetMetaData(key))
    assert "Bogus" not in sitk_image.GetMetaDataKeys()


@pytest.mark.parametrize(
    "test_img, center, width",
    [
        ("image3x4.mhd", "20.5", "200.5"),
        ("image3x4-len-1.mhd", "[20.5]", "[200.5]"),
        ("image3x4-len-2.mhd", "[10.5, 20.5]", "[100.5, 200.5]"),
    ],
)
def test_load_sitk_image_with_various_window_formats(
    test_img: str,
    center: Union[float, List[float]],
    width: Union[float, List[float]],
):
    src = MHD_WINDOW_DIR / test_img
    sitk_image = load_sitk_image(src)

    assert center == sitk_image.GetMetaData("WindowCenter")
    assert width == sitk_image.GetMetaData("WindowWidth")


@pytest.mark.parametrize(
    "test_img, error_msg",
    [
        ("image3x4-center-gt-width.mhd", "equal number"),
        ("image3x4-width-gt-center.mhd", "equal number"),
        ("image3x4-only-width-array.mhd", "different format"),
        ("image3x4-only-center-array.mhd", "different format"),
        ("image3x4-len-0.mhd", "does not match pattern"),
    ],
)
def test_load_sitk_image_with_faulty_window_formats(
    test_img: str, error_msg: str
):
    src = MHD_WINDOW_DIR / "errors" / test_img
    with pytest.raises(ValidationError, match=error_msg):
        load_sitk_image(src)


@pytest.mark.parametrize("test_img", ["image10x11x12x13.mhd", "image3x4.mhd"])
@pytest.mark.parametrize(
    ["key", "value"],
    [
        ("Exposures", "1 2 3e-5 4 5.2 6 7 8 9 10 11 12 13.0 e"),
        ("Exposures", "1 2 3e-5 4 5.2 6 7 8 9 10 11 12"),
        ("t0", "1 2"),
        ("t1", "string"),
        (
            "ContentTimes",
            ("245959.999 000000.000 111111.111 " * 4) + "121212.333",
        ),
        ("ContentTimes", "1 2 3e-5 4 5.2 6 7 8 9 10 11 12 13.0 14.0"),
    ],
)
def test_load_sitk_image_with_corrupt_additional_meta_data_fails(
    tmpdir, test_img: str, key: str, value: str
):
    src = RESOURCE_PATH / "image10x11x12x13.mhd"
    dest = Path(tmpdir) / src.name
    shutil.copy(str(src), str(dest))
    with open(str(dest)) as f:
        lines = f.readlines()
    lines.insert(-1, f"{key} = {value}\n")
    with open(str(dest), "w") as f:
        f.writelines(lines)
    with pytest.raises(ValidationError):
        load_sitk_image(dest)


def test_fail_on_invalid_utf8():
    with pytest.raises(ValidationError):
        parse_mh_header(RESOURCE_PATH / "invalid_utf8.mhd")


def test_too_many_headers_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        for i in range(1000000):
            f.write(f"key{i} = {i}\n")

    with pytest.raises(ValidationError):
        parse_mh_header(test_file_path)


def test_line_too_long(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("key = ")
        for i in range(1000000):
            f.write(f"{i}")

    with pytest.raises(ValidationError):
        parse_mh_header(test_file_path)


def test_does_not_choke_on_empty_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("\n")

    assert parse_mh_header(test_file_path) == {}


@pytest.mark.parametrize(
    "string",
    [
        "1",
        "1.001",
        "-1e10",
        "+1e10",
        "00400",
        "[1]",
        "[1.1]",
        "[1, 1]",
        "[1.1, 0]",
        "[0, 1.1]",
        "[-1e10, +100, 00400]",
        "[1, 2, 3, 4]",
        "[1,2,3,4]",
    ],
)
def test_regex_matching_float_arrays(string: str):
    assert FLOAT_OR_FLOAT_ARRAY_MATCH_REGEX.match(string)


@pytest.mark.parametrize(
    "string",
    [
        "",
        ".",
        "[]",
        "1,",
        "1,  ",
        "[1  ]",
        "[  1]",
        "[1",
        "1]",
        "[1,]",
        "[ 1]",
        "[ , ]",
        "[,]",
        "[1, 2, 3, 4,]",
    ],
)
def test_regex_non_matching_faulty_array_and_floats(string: str):
    assert not FLOAT_OR_FLOAT_ARRAY_MATCH_REGEX.match(string)
