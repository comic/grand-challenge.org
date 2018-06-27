import re
from uuid import UUID
import contextlib

import pytest
from django.http import HttpResponse
from django.test import Client, RequestFactory

from grandchallenge.cases import signals
from grandchallenge.cases.models import RawImageUploadSession
from tests.cases_tests import RESOURCE_PATH
from tests.cases_tests.job_test_utils import CeleryTaskCollector, replace_var
from tests.factories import SUPER_SECURE_TEST_PASSWORD
from tests.jqfileupload_tests.external_test_support import \
    create_file_from_filepath


@pytest.mark.django_db
def test_upload_some_images(client: Client, rf: RequestFactory, ChallengeSet):
    task_collector = CeleryTaskCollector(signals.build_images)
    with replace_var(signals, "build_images", task_collector):
        test_user = ChallengeSet.participant

        response = client.get("/cases/upload/")
        assert response.status_code != 200

        assert client.login(
            username=test_user.username,
            password=SUPER_SECURE_TEST_PASSWORD)

        response = client.get("/cases/upload/")
        response: HttpResponse
        assert response.status_code == 200

        file1 = create_file_from_filepath(RESOURCE_PATH / "image10x10x10.mha")

        response = client.post(
            "/cases/upload/",
            data={
                "files": f"{file1.uuid}",
            }
        )
        response: HttpResponse
        assert response.status_code == 302

        redirect_match = re.match(
            r"/cases/uploaded/(?P<uuid>[^/]+)/?$",
            response["Location"])
        assert redirect_match is not None
        assert RawImageUploadSession.objects.filter(
            pk=UUID(redirect_match.group("uuid"))).exists()

        response = client.get(response["Location"])
        response: HttpResponse
        assert response.status_code == 200
