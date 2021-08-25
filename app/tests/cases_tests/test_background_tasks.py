import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock

import SimpleITK
import pytest
from actstream.actions import is_following
from billiard.exceptions import SoftTimeLimitExceeded
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
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

    for name, db_object in uploaded_images.items():
        name: str
        db_object: RawImageFile

        db_object.refresh_from_db()

        assert db_object.staged_file_id is None
        if name in invalid_images:
            assert db_object.error is not None
        else:
            assert db_object.error is None


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

    raw_image_file = list(uploaded_images.values())[0]
    raw_image_file: RawImageFile
    raw_image_file.refresh_from_db()
    assert raw_image_file.staged_file_id is None

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

    raw_image_file: RawImageFile = list(uploaded_images.values())[0]
    raw_image_file.refresh_from_db()
    assert raw_image_file.staged_file_id is None

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

    no_image_image = list(uploaded_images.values())[0]
    no_image_image.refresh_from_db()
    assert no_image_image.error is not None

    lonely_mhd_image = list(uploaded_images.values())[1]
    lonely_mhd_image.refresh_from_db()
    assert lonely_mhd_image.error is not None

    sys_file_image = list(uploaded_images.values())[2]
    sys_file_image.refresh_from_db()
    assert sys_file_image.error is not None


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
    uploaded_images = RawImageFile.objects.filter(upload_session=session).all()
    assert len(uploaded_images) == 4

    session.refresh_from_db()
    assert session.status == session.SUCCESS
    assert session.error_message is None

    for raw_image in uploaded_images:
        raw_image.refresh_from_db()
        assert raw_image.error is not None


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

    raw_image_file = list(uploaded_images.values())[0]
    raw_image_file: RawImageFile
    raw_image_file.refresh_from_db()
    assert raw_image_file.staged_file_id is None

    image = images[0]
    assert image.shape == [7, 6, 5]
    assert image.shape_without_color == [7, 6, 5]
    assert image.color_space == Image.COLOR_SPACE_GRAY

    sitk_image = image.get_sitk_image()
    assert [e for e in reversed(sitk_image.GetSize())] == image.shape


@pytest.mark.parametrize("file_name", ("test.zip", "test.tar"))
def test_check_compressed_and_extract(tmpdir, file_name):
    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]

    tmpdir_path = Path(tmpdir)
    check_compressed_and_extract(tmp_file, tmpdir_path)

    expected = [
        os.path.join(tmpdir_path, "folder-0/file-0.txt"),
        os.path.join(tmpdir_path, "folder-0/folder-1/file-1.txt"),
        os.path.join(tmpdir_path, "folder-0/folder-1/folder-2/file-2.txt"),
        os.path.join(
            tmpdir_path, "folder-0/folder-1/folder-2/folder-3/file-3.txt"
        ),
    ]
    actual = []
    for root, _, files in os.walk(tmpdir_path):
        for file in files:
            actual.append(os.path.join(root, file))
    actual = sorted(actual)
    assert actual == expected


@pytest.mark.parametrize(
    "file_name", ("tar_with_link.tar", "tar_with_sym_link.tar",),
)
def test_check_compressed_and_extract_with_symlink(tmpdir, file_name):

    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]

    tmpdir_path = Path(tmpdir)
    with pytest.raises(ValidationError):
        check_compressed_and_extract(tmp_file, tmpdir_path)


@pytest.mark.parametrize("file_name", ("deep_folder.tar",))
def test_check_compressed_and_extract_with_deep_folder_structure(
    tmpdir, file_name
):

    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]

    tmpdir_path = Path(tmpdir)
    check_compressed_and_extract(tmp_file, tmpdir_path)
    expected = [
        os.path.join(
            tmpdir_path,
            # 15 folders deep, each folder (except the last) 255 characters long, repeated numbers 0-9.
            # single png at the deepest folder
            f"{('1234567890'*26)[:-5]}/" * 14 + f"{('1234567890'*24)}/t.png",
        ),
    ]
    actual = []
    for root, _, files in os.walk(tmpdir_path):
        for file in files:
            actual.append(os.path.join(root, file))
    actual = sorted(actual)
    assert actual == expected


@pytest.mark.parametrize(
    "file_name", ("same_name.zip", "same_name_zipped.zip")
)
def test_check_compressed_and_extract_same_name(tmpdir, file_name):
    file = RESOURCE_PATH / file_name
    tmp_file = shutil.copy(str(file), str(tmpdir))
    tmp_file = Path(tmp_file)
    assert tmpdir.listdir() == [tmp_file]
    file_basename, _ = os.path.splitext(file_name)
    tmpdir_path = Path(tmpdir)
    check_compressed_and_extract(tmp_file, tmpdir_path)
    expected = sorted(
        [
            os.path.join(
                tmpdir_path, file_basename, str(x), "1", "test_grayscale.png",
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
    assert session.error_message is None
    images = session.image_set.all()
    assert images.count() == 4
    # image10x10x10.mha image10x10x10.[mhd,zraw]
    assert (
        len([x for x in images if x.shape_without_color == [10, 10, 10]]) == 2
    )
    # dicom.tar
    assert (
        len([x for x in images if x.shape_without_color == [19, 4, 2, 3]]) == 1
    )
    # valid_tiff.tiff
    assert (
        len([x for x in images if x.shape_without_color == [1, 205, 205]]) == 1
    )


@pytest.mark.django_db
def test_build_multiple_zip_files(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # valid.zip contains a tarred version of the dicom folder,
    # image10x10x10.[mha,mhd,zraw] and valid_tiff.tiff
    images = ["valid.zip", "deep_folder.tar"]
    session, uploaded_images = create_raw_upload_image_session(images=images)

    session.refresh_from_db()
    assert session.error_message is None


@pytest.mark.django_db
def test_failed_dicom_files_are_retained(settings):
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    # A valid set of dicom images. Files should not be retained
    images = [f"dicom/{x}.dcm" for x in range(1, 21)]
    session, _ = create_raw_upload_image_session(images=images)
    session.refresh_from_db()

    assert Image.objects.count() == 1
    assert not any(
        RawImageFile.objects.values_list("staged_file_id", flat=True)
    )
    RawImageFile.objects.all().delete()

    # An invalid set of dicom images, but the creator is not in the dedicated
    # user group. Files should not be retained
    images = [f"dicom/{x}.dcm" for x in range(1, 22)]
    session, _ = create_raw_upload_image_session(images=images)
    session.refresh_from_db()

    assert Image.objects.count() == 1
    assert not any(
        RawImageFile.objects.values_list("staged_file_id", flat=True)
    )
    RawImageFile.objects.all().delete()

    # An invalid set of dicom images, and the creator is in the dedicated
    # user group. Files should be retained
    user = UserFactory()
    g = Group.objects.get(name=settings.DICOM_DATA_CREATORS_GROUP_NAME)
    g.user_set.add(user)
    session, _ = create_raw_upload_image_session(images=images, user=user)
    session.refresh_from_db()

    assert Image.objects.count() == 1
    assert all(RawImageFile.objects.values_list("staged_file_id", flat=True))
    RawImageFile.objects.all().delete()


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
