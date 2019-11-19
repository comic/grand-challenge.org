from unittest import mock

import pytest

from grandchallenge.cases.image_builders.dicom_4dct import (
    _get_headers,
    _validate_dicom_files,
    image_builder_dicom_4dct,
)
from tests.cases_tests import RESOURCE_PATH


DICOM_DIR = RESOURCE_PATH / "dicom"


def test_get_headers():
    headers = _get_headers(DICOM_DIR)
    assert [x["file"] for x in headers] == [
        f"{DICOM_DIR}/{x}.dcm" for x in range(1, 77)
    ]

    with pytest.raises(ValueError) as e:
        _get_headers(RESOURCE_PATH)
        assert "Invalid dicom file passed." in str(e)


def test_validate_dicom_files():
    headers, n_time, n_slices = _validate_dicom_files(DICOM_DIR)
    assert n_time == 19
    assert n_slices == 4
    with mock.patch(
        "grandchallenge.cases.image_builders.dicom_4dct._get_headers",
        return_value=headers[1:],
    ):
        with pytest.raises(ValueError) as e:
            _validate_dicom_files(DICOM_DIR)
            assert "Number of slices per time point varies" in str(e)


def test_image_builder_dicom_4dct():
    result = image_builder_dicom_4dct(DICOM_DIR)
    assert result.consumed_files == [
        f"{DICOM_DIR}/{x}.dcm" for x in range(1, 77)
    ]

    image = result.new_images[0]
    assert image.shape == [19, 4, 2, 3]
    assert len(result.new_image_files) == 2
