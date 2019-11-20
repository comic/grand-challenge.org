from unittest import mock

from grandchallenge.cases.image_builders.dicom_4dct import (
    _get_headers_by_study,
    _validate_dicom_files,
    image_builder_dicom_4dct,
)
from tests.cases_tests import RESOURCE_PATH


DICOM_DIR = RESOURCE_PATH / "dicom"


def test_get_headers_by_study():
    studies = _get_headers_by_study(DICOM_DIR)
    assert len(studies) == 1
    for key in studies:
        assert [str(x["file"]) for x in studies[key]["headers"]] == [
            f"{DICOM_DIR}/{x}.dcm" for x in range(1, 77)
        ]

    studies = _get_headers_by_study(RESOURCE_PATH)
    assert len(studies) == 0


def test_validate_dicom_files():
    studies = _validate_dicom_files(DICOM_DIR)
    assert len(studies) == 1
    for study in studies:
        headers = study.headers
        assert study.n_time == 19
        assert study.n_slices == 4
    with mock.patch(
        "grandchallenge.cases.image_builders.dicom_4dct._get_headers_by_study",
        return_value={"foo": {"headers": headers[1:], "file": "bar"}},
    ):
        studies = _validate_dicom_files(DICOM_DIR)
        assert len(studies) == 0


def test_image_builder_dicom_4dct():
    result = image_builder_dicom_4dct(DICOM_DIR)
    assert result.consumed_files == [f"{x}.dcm" for x in range(1, 77)]

    image = result.new_images[0]
    assert image.shape == [19, 4, 2, 3]
    assert len(result.new_image_files) == 2
