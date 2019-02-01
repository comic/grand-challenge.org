from typing import List, Tuple, Dict

import pytest

from grandchallenge.cases.models import (
    RawImageFile,
    RawImageUploadSession,
    UPLOAD_SESSION_STATE,
    Image,
)
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from tests.cases_tests import RESOURCE_PATH
from tests.jqfileupload_tests.external_test_support import (
    create_file_from_filepath
)


def create_raw_upload_image_session(
    images: List[str], delete_file=False, imageset=None, annotationset=None
) -> Tuple[RawImageUploadSession, Dict[str, RawImageFile]]:
    upload_session = RawImageUploadSession(
        imageset=imageset, annotationset=annotationset
    )

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

    return upload_session, uploaded_images


@pytest.mark.django_db
def test_file_session_creation():
    images = ["image10x10x10.zraw"]
    _, uploaded_images = create_raw_upload_image_session(images)

    assert len(uploaded_images) == 1
    assert uploaded_images[images[0]].staged_file_id is not None

    aFile = StagedAjaxFile(uploaded_images[images[0]].staged_file_id)
    assert aFile.exists


@pytest.mark.django_db
def test_image_file_creation(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    # with replace_var(signals, "build_images", task_collector):
    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.mha",
        "image10x10x10-extra-stuff.mhd",
        "invalid_utf8.mhd",
        "no_image",
        "valid_tiff.tif",
        "invalid_tiles_tiff.tif",
    ]
    session, uploaded_images = create_raw_upload_image_session(images)

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is None

    assert Image.objects.filter(origin=session).count() == 4

    for name, db_object in uploaded_images.items():
        name: str
        db_object: RawImageFile

        db_object.refresh_from_db()

        assert db_object.staged_file_id is None
        if name in ("no_image", "invalid_utf8.mhd", "invalid_tiles_tiff.tif"):
            assert db_object.error is not None
        else:
            assert db_object.error is None


@pytest.mark.django_db
def test_staged_uploaded_file_cleanup_interferes_with_image_build(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    images = ["image10x10x10.zraw", "image10x10x10.mhd"]
    session, uploaded_images = create_raw_upload_image_session(
        images, delete_file=True
    )

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is not None


@pytest.mark.django_db
def test_no_convertible_file(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    images = ["no_image", "image10x10x10.mhd", "referring_to_system_file.mhd"]
    session, uploaded_images = create_raw_upload_image_session(images)

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is None

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
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.zraw",
        "image10x10x10.mhd",
    ]
    session, uploaded_images = create_raw_upload_image_session(images)
    uploaded_images = RawImageFile.objects.filter(upload_session=session).all()
    assert len(uploaded_images) == 4

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is None

    for raw_image in uploaded_images:
        raw_image.refresh_from_db()
        assert raw_image.error is not None


@pytest.mark.django_db
def test_mhd_file_annotation_creation(settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    images = ["image5x6x7.mhd", "image5x6x7.zraw"]
    session, uploaded_images = create_raw_upload_image_session(images)

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is None

    images = Image.objects.filter(origin=session).all()
    assert len(images) == 1

    raw_image_file = list(uploaded_images.values())[0]
    raw_image_file: RawImageFile
    raw_image_file.refresh_from_db()
    assert raw_image_file.staged_file_id is None

    image = images[0]
    assert image.shape == [5, 6, 7]
    assert image.shape_without_color == [5, 6, 7]
    assert image.color_space == Image.COLOR_SPACE_GRAY
