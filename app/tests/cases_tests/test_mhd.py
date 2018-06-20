"""
Tests for the mhd-file reconstruction.
"""

import shutil

import pytest

from grandchallenge.cases.tasks import parse_mh_header
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

