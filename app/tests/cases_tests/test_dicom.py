from unittest import mock

import numpy as np
import pydicom

from grandchallenge.cases.image_builders.dicom_4dct import (
    _get_headers_by_study,
    _validate_dicom_files,
    image_builder_dicom_4dct,
)
from grandchallenge.cases.image_builders.metaio_utils import parse_mh_header
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
    assert len(result.new_image_files) == 1
    mha_file_obj = [
        x for x in result.new_image_files if x.file.name.endswith("mha")
    ][0]

    headers = parse_mh_header(mha_file_obj.file)

    direction = headers["TransformMatrix"].split()
    origin = headers["Offset"].split()
    spacing = headers["ElementSpacing"].split()
    exposures = headers["Exposures"].split()
    content_times = headers["ContentTimes"].split()

    assert len(exposures) == 19
    assert exposures == [str(x) for x in range(100, 2000, 100)]
    assert len(content_times) == 19
    assert content_times == [str(x) for x in range(214501, 214520)]

    dcm_ref = pydicom.dcmread(str(DICOM_DIR / "1.dcm"))
    assert np.array_equal(
        np.array(list(map(float, direction))).reshape((4, 4)), np.eye(4)
    )
    assert np.allclose(
        list(map(float, spacing)),
        list(
            map(
                float,
                list(dcm_ref.PixelSpacing) + [dcm_ref.SliceThickness] + [1.0],
            )
        ),
    )
    assert np.allclose(
        list(map(float, origin)),
        list(map(float, dcm_ref.ImagePositionPatient)) + [0.0],
    )
