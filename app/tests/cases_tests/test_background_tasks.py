from pathlib import Path

import pytest

from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from grandchallenge.cases.tasks import build_images
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile
from tests.jqfileupload_tests.external_test_support import \
    create_file_from_filepath


BASE_PATH = Path(__file__).parent.absolute()
RESOURCE_PATH = BASE_PATH / "resources"


def create_raw_upload_image_session(images):
    upload_session = RawImageUploadSession.objects.create()
    uploaded_images = {}
    for image in images:
        staged_file = create_file_from_filepath(RESOURCE_PATH / image)
        image = RawImageFile.objects.create(
            upload_session=upload_session,
            staged_file_id=staged_file.uuid,
        )
        uploaded_images[staged_file.name] = uploaded_images
    return upload_session, uploaded_images


@pytest.mark.django_db
def test_mhd_file_creation():
    images = [
        "image10x10x10.zraw",
        "image10x10x10.mhd",
        "image10x10x10.mha",
        "no_image",
    ]
    session, uploaded_images = create_raw_upload_image_session(images)

    build_images(session.pk)



