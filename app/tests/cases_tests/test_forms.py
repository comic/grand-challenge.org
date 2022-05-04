import pytest
from django.test import Client
from django_capture_on_commit_callbacks import capture_on_commit_callbacks

from grandchallenge.cases.models import RawImageUploadSession
from tests.cases_tests import RESOURCE_PATH
from tests.factories import UserFactory
from tests.reader_studies_tests.factories import ReaderStudyFactory
from tests.uploads_tests.factories import create_upload_from_file
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_some_images(client: Client, challenge_set, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()

    # Use reader studies as this uses UploadRawImagesForm
    rs = ReaderStudyFactory()
    rs.add_editor(user)

    response = get_view_for_user(
        client=client,
        viewname="reader-studies:add-images",
        user=user,
        reverse_kwargs={"slug": rs.slug},
    )
    assert response.status_code == 200

    assert rs.images.count() == 0
    assert RawImageUploadSession.objects.count() == 0

    user_upload = create_upload_from_file(
        file_path=RESOURCE_PATH / "image10x10x10.mha", creator=user
    )

    with capture_on_commit_callbacks(execute=True):
        response = get_view_for_user(
            data={"user_uploads": [user_upload.pk]},
            client=client,
            viewname="reader-studies:add-images",
            user=user,
            reverse_kwargs={"slug": rs.slug},
            method=client.post,
        )

    assert response.status_code == 302
    assert rs.images.count() == 1
    sessions = RawImageUploadSession.objects.all()
    assert len(sessions) == 1

    response = get_view_for_user(
        url=sessions[0].get_absolute_url(), client=client, user=user
    )
    assert response.status_code == 200

    response = get_view_for_user(
        url=sessions[0].get_absolute_url(),
        client=client,
        user=UserFactory(is_staff=True),
    )
    assert response.status_code == 403
