import os
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from unittest import mock

import numpy as np
import pydicom
import pytest
from panimg.image_builders.dicom import (
    _get_headers_by_study,
    _validate_dicom_files,
    format_error,
    image_builder_dicom,
)
from panimg.image_builders.metaio_utils import parse_mh_header
from panimg.panimg import _build_files

from grandchallenge.cases.models import Image
from tests.cases_tests import RESOURCE_PATH

DICOM_DIR = RESOURCE_PATH / "dicom"


def test_get_headers_by_study():
    files = [Path(d[0]).joinpath(f) for d in os.walk(DICOM_DIR) for f in d[2]]
    studies = _get_headers_by_study(files, defaultdict(list))
    assert len(studies) == 1
    for key in studies:
        assert [str(x["file"]) for x in studies[key]["headers"]] == [
            f"{DICOM_DIR}/{x}.dcm" for x in range(1, 77)
        ]

    for root, _, files in os.walk(RESOURCE_PATH):
        files = [Path(root).joinpath(f) for f in files]
        break

    studies = _get_headers_by_study(files, defaultdict(list))
    assert len(studies) == 0


def test_validate_dicom_files():
    files = [Path(d[0]).joinpath(f) for d in os.walk(DICOM_DIR) for f in d[2]]
    studies = _validate_dicom_files(files, defaultdict(list))
    assert len(studies) == 1
    for study in studies:
        headers = study.headers
        assert study.n_time == 19
        assert study.n_slices == 4
    with mock.patch(
        "panimg.image_builders.dicom._get_headers_by_study",
        return_value={
            "foo": {"headers": headers[1:], "file": "bar", "index": 1},
        },
    ):
        errors = defaultdict(list)
        studies = _validate_dicom_files(files, errors)
        assert len(studies) == 0
        for header in headers[1:]:
            assert errors[header["file"]] == [
                format_error("Number of slices per time point differs")
            ]


def test_image_builder_dicom_4dct(tmpdir):
    files = {Path(d[0]).joinpath(f) for d in os.walk(DICOM_DIR) for f in d[2]}
    result = _build_files(
        builder=image_builder_dicom, files=files, output_directory=tmpdir
    )
    assert result.consumed_files == {
        Path(DICOM_DIR).joinpath(f"{x}.dcm") for x in range(1, 77)
    }

    assert len(result.new_images) == 1
    image = Image(**asdict(result.new_images.pop()))
    assert image.shape == [19, 4, 2, 3]
    assert len(result.new_image_files) == 1
    mha_file_obj = [
        x for x in result.new_image_files if x.file.suffix == ".mha"
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
        list(map(float, spacing))[:2],
        list(map(float, list(dcm_ref.PixelSpacing),)),
    )
    assert np.allclose(
        list(map(float, origin)),
        list(map(float, dcm_ref.ImagePositionPatient)) + [0.0],
    )


@pytest.mark.parametrize(
    "folder,element_type",
    [
        ("dicom", "MET_SHORT"),
        ("dicom_intercept", "MET_FLOAT"),
        ("dicom_slope", "MET_FLOAT"),
    ],
)
def test_dicom_rescaling(folder, element_type, tmpdir):
    """
    2.dcm in dicom_intercept and dicom_slope has been modified to add a
    small intercept (0.01) or slope (1.001) respectively.
    """
    files = [
        Path(d[0]).joinpath(f)
        for d in os.walk(RESOURCE_PATH / folder)
        for f in d[2]
    ]
    result = _build_files(
        builder=image_builder_dicom, files=files, output_directory=tmpdir
    )

    assert len(result.new_image_files) == 1
    mha_file_obj = [
        x for x in result.new_image_files if x.file.suffix == ".mha"
    ][0]

    headers = parse_mh_header(mha_file_obj.file)
    assert headers["ElementType"] == element_type


def test_dicom_window_level(tmpdir):
    files = {
        Path(d[0]).joinpath(f)
        for d in os.walk(RESOURCE_PATH / "dicom")
        for f in d[2]
    }
    result = _build_files(
        builder=image_builder_dicom, files=files, output_directory=tmpdir
    )

    assert len(result.new_image_files) == 1
    mha_file_obj = [
        x for x in result.new_image_files if x.file.suffix == ".mha"
    ][0]

    headers = parse_mh_header(mha_file_obj.file)
    assert headers["WindowCenter"] == "30"
    assert headers["WindowWidth"] == "200"

    assert len(result.new_images) == 1
    image_obj = result.new_images.pop()
    assert image_obj.window_center == 30.0
    assert image_obj.window_width == 200.0
