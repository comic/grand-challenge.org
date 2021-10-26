import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import SimpleITK
import pytest
from actstream.actions import is_following
from billiard.exceptions import SoftTimeLimitExceeded
from django_capture_on_commit_callbacks import capture_on_commit_callbacks
from panimg.image_builders.metaio_utils import (
    ADDITIONAL_HEADERS,
    EXPECTED_HEADERS,
    HEADERS_MATCHING_NUM_TIMEPOINTS,
    parse_mh_header,
)

from grandchallenge.cases.models import (
    Image,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.cases.tasks import (
    build_images,
    check_compressed_and_extract,
)
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from grandchallenge.notifications.models import Notification
from tests.cases_tests import RESOURCE_PATH
from tests.factories import UploadSessionFactory, UserFactory
from tests.jqfileupload_tests.external_test_support import (
    create_file_from_filepath,
)


def create_raw_upload_image_session(
    *, images: List[str], delete_file=False, user=None, linked_task=None,
) -> Tuple[RawImageUploadSession, Dict[str, RawImageFile]]:
    creator = user or UserFactory(email="test@example.com")
    upload_session = RawImageUploadSession(creator=creator)

    uploaded_images = {}
    for image in images:
        staged_file = create_file_from_filepath(RESOURCE_PATH / image)
        image = RawImageFile.objects.create(
            upload_session=upload_session,
            filename=staged_file.name,
            staged_file_id=staged_file.uuid,
        )
        uploaded_images[staged_file.name] = image

    if delete_file:
        StagedAjaxFile(
            uploaded_images["image10x10x10.zraw"].staged_file_id
        ).delete()

    upload_session.save()

    with capture_on_commit_callbacks(execute=True):
        upload_session.process_images(linked_task=linked_task)

    return upload_session, uploaded_images


@pytest.mark.django_db
def test_file_session_creation():
    images = ["image10x10x10.zraw"]
    _, uploaded_images = create_raw_upload_image_session(images=images)

    assert len(uploaded_images) == 1
    assert uploaded_images[images[0]].staged_file_id is not None

    a_file = StagedAjaxFile(uploaded_images[images[0]].staged_file_id)
    assert a_file.exists


@pytest.mark.django_db
def test_image_file_creation(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # with replace_var(signals, "build_images", task_collector):
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
    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert f"{len(invalid_images)} file" in session.error_message

    assert Image.objects.filter(origin=session).count() == 5

    assert not RawImageFile.objects.exists()

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


@pytest.mark.django_db
def test_staged_uploaded_file_cleanup_interferes_with_image_build(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    images = ["image10x10x10.zraw", "image10x10x10.mhd"]
    session, uploaded_images = create_raw_upload_image_session(
        images=images, delete_file=True
    )

    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert session.error_message is not None


@pytest.mark.parametrize(
    "images",
    (
        ["image10x11x12x13.mha"],
        ["image10x11x12x13.mhd", "image10x11x12x13.zraw"],
    ),
)
@pytest.mark.django_db
def test_staged_4d_mha_and_4d_mhd_upload(settings, images: List):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert session.error_message is None

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    assert not RawImageFile.objects.exists()

    image = images[0]
    assert image.shape == [13, 12, 11, 10]
    assert image.shape_without_color == [13, 12, 11, 10]
    assert image.color_space == Image.COLOR_SPACE_GRAY

    sitk_image = image.get_sitk_image()
    assert [e for e in reversed(sitk_image.GetSize())] == image.shape


@pytest.mark.parametrize(
    "images",
    (
        ["image10x11x12x13-extra-stuff.mhd", "image10x11x12x13.zraw"],
        ["image3x4-extra-stuff.mhd", "image3x4.zraw"],
    ),
)
@pytest.mark.django_db
def test_staged_mhd_upload_with_additional_headers(
    settings, tmp_path, images: List[str]
):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert session.error_message is None

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    assert not RawImageFile.objects.exists()

    image: Image = images[0]
    tmp_header_filename = tmp_path / "tmp_header.mhd"
    with image.files.get(file__endswith=".mha").file.open(
        "rb"
    ) as in_file, open(tmp_header_filename, "wb") as out_file:
        out_file.write(in_file.read())

    headers = parse_mh_header(tmp_header_filename)
    for key in headers.keys():
        assert (key in ADDITIONAL_HEADERS) or (key in EXPECTED_HEADERS)

    sitk_image: SimpleITK.Image = image.get_sitk_image()
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
def test_no_convertible_file(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    images = ["no_image", "image10x10x10.mhd", "referring_to_system_file.mhd"]
    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert f"{len(images)} file" in session.error_message

    assert not RawImageFile.objects.exists()

    assert session.import_result["consumed_files"] == []
    assert {*session.import_result["file_errors"]} == {*images}


@pytest.mark.django_db
def test_errors_on_files_with_duplicate_file_names(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.zraw",
        "image10x10x10.mhd",
    ]
    session, uploaded_images = create_raw_upload_image_session(images=images)

    assert not RawImageFile.objects.exists()
    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert session.error_message == "Duplicate files uploaded"
    assert session.import_result is None


@pytest.mark.django_db
def test_mhd_file_annotation_creation(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    images = ["image5x6x7.mhd", "image5x6x7.zraw"]
    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert session.error_message is None

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    assert not RawImageFile.objects.exists()

    image = images[0]
    assert image.shape == [7, 6, 5]
    assert image.shape_without_color == [7, 6, 5]
    assert image.color_space == Image.COLOR_SPACE_GRAY

    sitk_image = image.get_sitk_image()
    assert [e for e in reversed(sitk_image.GetSize())] == image.shape


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
        [
            os.path.join(
                tmpdir_path,
                file_name,
                f"{x}.zip" if double_zipped else f"{x}/1",
                "test_grayscale.png",
            )
            for x in range(1, 11)
        ]
    )
    actual = []
    for root, _, files in os.walk(tmpdir_path):
        for file in files:
            actual.append(os.path.join(root, file))
    actual = sorted(actual)
    assert actual == expected


@pytest.mark.django_db
def test_build_zip_file(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # valid.zip contains a tarred version of the dicom folder,
    # image10x10x10.[mha,mhd,zraw] and valid_tiff.tiff
    images = ["valid.zip"]
    session, uploaded_images = create_raw_upload_image_session(images=images)

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
@mock.patch(
    "grandchallenge.cases.tasks._handle_raw_image_files",
    side_effect=SoftTimeLimitExceeded(),
)
def test_soft_time_limit(_):
    session = UploadSessionFactory()
    session.status = session.REQUEUED
    session.save()
    build_images(upload_session_pk=session.pk)
    session.refresh_from_db()
    assert session.status == session.FAILURE
    assert session.error_message == "Time limit exceeded."


@pytest.mark.django_db
def test_failed_image_import_notification():
    image = ["corrupt.png"]
    session, _ = create_raw_upload_image_session(images=image)

    build_images(upload_session_pk=session.pk)
    session.refresh_from_db()

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
