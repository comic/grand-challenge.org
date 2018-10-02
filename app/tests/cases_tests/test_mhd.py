"""
Tests for the mhd-file reconstruction.
"""

import shutil
from pathlib import Path

import pytest

from grandchallenge.cases.image_builders.metaio_mhd_mha import parse_mh_header
from tests.cases_tests import RESOURCE_PATH


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


def test_fail_on_invalid_utf8():
    with pytest.raises(ValueError):
        parse_mh_header(RESOURCE_PATH / "invalid_utf8.mhd")


def test_too_many_headers_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        for i in range(1000000):
            f.write("key{i} = {i}\n")

    with pytest.raises(ValueError):
        parse_mh_header(test_file_path)


def test_line_too_long(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("key = ")
        for i in range(1000000):
            f.write("{i}")

    with pytest.raises(ValueError):
        parse_mh_header(test_file_path)


def test_does_not_choke_on_empty_file(tmpdir):
    # Generate test file...
    test_file_path = Path(tmpdir) / "test.mhd"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("\n")

    assert parse_mh_header(test_file_path) == {}
