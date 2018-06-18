from pathlib import Path
from typing import List, Tuple, Dict

import pytest

from grandchallenge.cases import signals
from grandchallenge.cases.models import RawImageFile, RawImageUploadSession, \
    UPLOAD_SESSION_STATE
from grandchallenge.cases.tasks import build_images
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from tests.jqfileupload_tests.external_test_support import \
    create_file_from_filepath


BASE_PATH = Path(__file__).parent.absolute()
RESOURCE_PATH = BASE_PATH / "resources"

# We need more control over whn jobs are emitted, so lets just disable the
# signal
signals.PREVENT_JOB_CREATION_ON_SAVE = True


def create_raw_upload_image_session(
        images: List[str]) -> Tuple[RawImageUploadSession, Dict[str, RawImageFile]]:
    upload_session = RawImageUploadSession.objects.create()
    uploaded_images = {}
    for image in images:
        staged_file = create_file_from_filepath(RESOURCE_PATH / image)
        image = RawImageFile.objects.create(
            upload_session=upload_session,
            staged_file_id=staged_file.uuid,
        )
        uploaded_images[staged_file.name] = image
    return upload_session, uploaded_images


@pytest.mark.django_db
def test_file_session_creation():
    images = [
        "image10x10x10.zraw",
    ]
    _, uploaded_images = create_raw_upload_image_session(images)

    assert len(uploaded_images) == 1
    assert uploaded_images[images[0]].staged_file_id is not None

    aFile = StagedAjaxFile(uploaded_images[images[0]].staged_file_id)
    assert aFile.exists


@pytest.mark.django_db
def test_mhd_file_creation():
    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.mha",
        "no_image",
    ]
    session, uploaded_images = create_raw_upload_image_session(images)

    session.session_state = UPLOAD_SESSION_STATE.queued
    session.save()

    build_images(session.pk)

    session.refresh_from_db()
    assert session.session_state == UPLOAD_SESSION_STATE.stopped
    assert session.error_message is None

    for name, db_object in uploaded_images.items():
        name: str
        db_object: RawImageFile

        db_object.refresh_from_db()

        assert db_object.staged_file_id is None
        if name == "no_image":
            assert db_object.error is not None
        else:
            assert db_object.error is None

