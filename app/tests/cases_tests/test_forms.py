import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.views import View

from grandchallenge.cases.views import UploadRawFiles
from tests.factories import UserFactory


@pytest.mark.django_db
def test_upload_some_images(client: Client, rf: RequestFactory):
    """
    Not working?! :-(
     - something with template tags goes wrong here...


    response = client.get("/cases/upload/")
    assert response.status_code != 200

    client.force_login(test_user)

    response = client.get("/cases/upload/")
    assert response.status_code == 200
    """
    test_user = UserFactory()

    upload_view = UploadRawFiles.as_view()
    upload_view: View

    req = rf.get("/cases/upload/")
    req.user = AnonymousUser()
    response = upload_view(req)
    response: HttpResponse
    assert response.status_code != 200

    req.user = test_user
    response = upload_view(req)
    response: HttpResponse
    assert response.status_code == 200

