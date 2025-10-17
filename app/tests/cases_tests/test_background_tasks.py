import os
import shutil
from pathlib import Path

import pytest
from actstream.actions import is_following
from billiard.exceptions import SoftTimeLimitExceeded
from panimg.image_builders.metaio_utils import (
    ADDITIONAL_HEADERS,
    EXPECTED_HEADERS,
    HEADERS_MATCHING_NUM_TIMEPOINTS,
    parse_mh_header,
)

from grandchallenge.cases.models import Image, RawImageUploadSession
from grandchallenge.cases.tasks import check_compressed_and_extract
from grandchallenge.notifications.models import Notification
from tests.cases_tests import RESOURCE_PATH
from tests.factories import UploadSessionFactory
from tests.utils import create_raw_upload_image_session


@pytest.mark.django_db
def test_image_file_creation(settings, django_capture_on_commit_callbacks):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.mha",
        "image10x11x12x13.mhd",
        "image10x11x12x13.zraw",
        "image10x10x10-extra-stuff.mhd",
        "invalid_utf8.mhd",
        "no_image",
        "valid_tiff.tif",
        "invalid_resolutions_tiff.tif",
    ]

    invalid_images = (
        "no_image",
        "invalid_utf8.mhd",
        "invalid_resolutions_tiff.tif",
    )
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert f"{len(invalid_images)} file" in session.error_message

    assert Image.objects.filter(origin=session).count() == 5

    assert {*session.import_result["consumed_files"]} == {
        "valid_tiff.tif",
        "image10x10x10.mha",
        "image10x10x10-extra-stuff.mhd",
        "image10x11x12x13.mhd",
        "image10x10x10.mhd",
        "image10x11x12x13.zraw",
        "image10x10x10.zraw",
    }
    assert {*session.import_result["file_errors"]} == {*invalid_images}


@pytest.mark.parametrize(
    "images",
    (
        ["image10x11x12x13-extra-stuff.mhd", "image10x11x12x13.zraw"],
        ["image3x4-extra-stuff.mhd", "image3x4.zraw"],
    ),
)
@pytest.mark.django_db
def test_staged_mhd_upload_with_additional_headers(
    settings, tmp_path, images: list[str], django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert not session.error_message

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    image: Image = images[0]
    tmp_header_filename = tmp_path / "tmp_header.mhd"
    with (
        image.files.get(file__endswith=".mha").file.open("rb") as in_file,
        open(tmp_header_filename, "wb") as out_file,
    ):
        out_file.write(in_file.read())

    headers = parse_mh_header(tmp_header_filename)
    for key in headers.keys():
        assert (key in ADDITIONAL_HEADERS) or (key in EXPECTED_HEADERS)

    sitk_image = image.sitk_image
    for key in ADDITIONAL_HEADERS:
        assert key in sitk_image.GetMetaDataKeys()
        if key in HEADERS_MATCHING_NUM_TIMEPOINTS:
            if sitk_image.GetDimension() >= 4:
                assert (
                    len(sitk_image.GetMetaData(key).split(" "))
                    == sitk_image.GetSize()[3]
                )
            else:
                assert len(sitk_image.GetMetaData(key).split(" ")) == 1
    assert "Bogus" not in sitk_image.GetMetaDataKeys()


@pytest.mark.django_db
def test_no_convertible_file(settings, django_capture_on_commit_callbacks):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    images = ["no_image", "image10x10x10.mhd", "referring_to_system_file.mhd"]
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert f"{len(images)} file" in session.error_message

    assert session.import_result["consumed_files"] == []
    assert {*session.import_result["file_errors"]} == {*images}


@pytest.mark.django_db
def test_errors_on_files_with_duplicate_file_names(
    settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.zraw",
        "image10x10x10.mhd",
    ]
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert (
        session.error_message
        == "Duplicate files uploaded, please try again with a unique set of files"
    )
    assert session.import_result is None


@pytest.mark.django_db
def test_mhd_file_annotation_creation(
    settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    images = ["image5x6x7.mhd", "image5x6x7.zraw"]
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert not session.error_message

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    image = images[0]
    assert image.shape == [7, 6, 5]
    assert image.shape_without_color == [7, 6, 5]
    assert image.color_space == Image.COLOR_SPACE_GRAY

    assert [e for e in reversed(image.sitk_image.GetSize())] == image.shape


def test_check_compressed_and_extract(tmpdir):
    file_name = "test.zip"
    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]

    tmpdir_path = Path(tmpdir)
    check_compressed_and_extract(src_path=tmp_file, checked_paths=set())

    expected = [
        os.path.join(tmpdir_path, file_name, "file-0.txt"),
        os.path.join(tmpdir_path, file_name, "folder-1/file-1.txt"),
        os.path.join(tmpdir_path, file_name, "folder-1/folder-2/file-2.txt"),
        os.path.join(
            tmpdir_path, file_name, "folder-1/folder-2/folder-3.zip/file-3.txt"
        ),
    ]
    actual = []
    for root, _, files in os.walk(tmpdir_path):
        for file in files:
            actual.append(os.path.join(root, file))
    actual = sorted(actual)
    assert actual == expected


@pytest.mark.parametrize(
    "file_name,double_zipped",
    (("same_name.zip", False), ("same_name_zipped.zip", True)),
)
def test_check_compressed_and_extract_same_name(
    tmpdir, file_name, double_zipped
):
    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]
    tmpdir_path = Path(tmpdir)
    check_compressed_and_extract(src_path=tmp_file, checked_paths=set())
    expected = sorted(
        os.path.join(
            tmpdir_path,
            file_name,
            f"{x}.zip" if double_zipped else f"{x}/1",
            "test_grayscale.png",
        )
        for x in range(1, 11)
    )
    actual = []
    for root, _, files in os.walk(tmpdir_path):
        for file in files:
            actual.append(os.path.join(root, file))
    actual = sorted(actual)
    assert actual == expected


@pytest.mark.django_db
def test_build_zip_file(settings, django_capture_on_commit_callbacks):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    # valid.zip contains a tarred version of the dicom folder,
    # image10x10x10.[mha,mhd,zraw] and valid_tiff.tiff
    images = ["valid.zip"]
    session, uploaded_images = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert len(session.import_result["consumed_files"]) == 4
    # No tar support
    assert {*session.import_result["file_errors"].keys()} == {
        "valid.zip/dicom.tar"
    }

    images = session.image_set.all()
    assert images.count() == 3
    # image10x10x10.mha image10x10x10.[mhd,zraw]
    assert (
        len([x for x in images if x.shape_without_color == [10, 10, 10]]) == 2
    )
    # valid_tiff.tiff
    assert (
        len([x for x in images if x.shape_without_color == [1, 205, 205]]) == 1
    )


@pytest.mark.django_db
def test_soft_time_limit(settings, django_capture_on_commit_callbacks, mocker):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    session = UploadSessionFactory()
    session.status = session.PENDING
    session.save()

    mocker.patch(
        "grandchallenge.cases.tasks._handle_raw_files",
        side_effect=SoftTimeLimitExceeded(),
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert session.error_message == "Time limit exceeded"


@pytest.mark.django_db
def test_failed_image_import_notification(
    settings, django_capture_on_commit_callbacks
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True

    images = ["corrupt.png"]
    session, _ = create_raw_upload_image_session(
        image_paths=[RESOURCE_PATH / p for p in images],
    )

    with django_capture_on_commit_callbacks(execute=True):
        session.process_images()

    assert RawImageUploadSession.objects.count() == 1
    assert is_following(
        user=RawImageUploadSession.objects.get().creator,
        obj=RawImageUploadSession.objects.get(),
    )
    assert Notification.objects.count() == 1
    assert (
        Notification.objects.get().user
        == RawImageUploadSession.objects.get().creator
    )
