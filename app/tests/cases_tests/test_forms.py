import re
from uuid import UUID

import pytest
from django.test import Client

from grandchallenge.cases.models import RawImageUploadSession
from tests.cases_tests import RESOURCE_PATH
from tests.factories import SUPER_SECURE_TEST_PASSWORD, UserFactory
from tests.jqfileupload_tests.external_test_support import (
    create_file_from_filepath
)


@pytest.mark.django_db
def test_upload_some_images(client: Client, ChallengeSet, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)
    settings.broker_url = ("memory://",)
    settings.backend = "memory"

    response = client.get("/cases/uploads/")
    assert response.status_code != 200

    staff_user = UserFactory(is_staff=True)

    assert client.login(
        username=staff_user.username, password=SUPER_SECURE_TEST_PASSWORD
    )

    response = client.get("/cases/uploads/")
    assert response.status_code == 200

    file1 = create_file_from_filepath(RESOURCE_PATH / "image10x10x10.mha")

    response = client.post("/cases/uploads/", data={"files": f"{file1.uuid}"})
    assert response.status_code == 302

    redirect_match = re.search(
        r"/cases/uploads/(?P<uuid>[^/]+)/?$", response["Location"]
    )

    assert redirect_match is not None
    assert RawImageUploadSession.objects.filter(
        pk=UUID(redirect_match.group("uuid"))
    ).exists()

    response = client.get(response["Location"])
    assert response.status_code == 200
