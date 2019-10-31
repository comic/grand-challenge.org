import pytest
from tests.utils import get_view_for_user
from tests.factories import UserFactory
from tests.cases_tests.factories import (
    RawImageUploadSessionFactory,
    RawImageFileFactory,
)
from tests.algorithms_tests.factories import AlgorithmImageFactory

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile
from grandchallenge.subdomains.utils import reverse

from rest_framework.authtoken.models import Token


@pytest.mark.django_db
def test_upload_session_list(client):
    upload_session_1, upload_session_2 = (
        RawImageUploadSessionFactory(),
        RawImageUploadSessionFactory(),
    )
    token = Token.objects.create(user=UserFactory())
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "get")(
        reverse("api:upload-session-list"), **extra_headers
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0

    token = Token.objects.create(user=UserFactory(is_superuser=True))
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "get")(
        reverse(
            "api:upload-session-detail", kwargs={"pk": upload_session_1.pk}
        ),
        **extra_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_upload_sessions_create(client):
    algo = AlgorithmImageFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"algorithm_image": algo.api_url},
        content_type="application/json",
    )
    assert response.status_code == 201

    upload_session = RawImageUploadSession.objects.get(
        pk=response.data.get("pk")
    )
    assert upload_session.algorithm_image == algo


@pytest.mark.django_db
def test_invalid_upload_sessions(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"algorithm_image": None},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "algorithm_image": ["This field may not be null."]
    }


@pytest.mark.django_db
def test_empty_data_upload_sessions(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"algorithm_image": ["This field is required."]}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_staff, expected_response", [(False, 201), (True, 201)]
)
def test_upload_session_post_permissions(client, is_staff, expected_response):
    algo = AlgorithmImageFactory()
    token = Token.objects.create(user=UserFactory(is_staff=is_staff))
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "post")(
        reverse("api:upload-session-list"),
        data={"algorithm_image": algo.api_url},
        **extra_headers,
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_image_file_list(client):
    dummy_file = RawImageFileFactory()

    token = Token.objects.create(user=UserFactory())
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "get")(
        reverse("api:image-file-list"), **extra_headers
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0

    token = Token.objects.create(user=UserFactory(is_superuser=True))
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "get")(
        reverse("api:image-file-detail", kwargs={"pk": dummy_file.pk}),
        **extra_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_image_file_create(client):
    upload_session = RawImageUploadSessionFactory()
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:image-file-list",
        user=user,
        client=client,
        method=client.post,
        data={
            "upload_session": upload_session.api_url,
            "filename": "dummy.bin",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    image_file = RawImageFile.objects.get(pk=response.data.get("pk"))
    assert image_file.upload_session == upload_session


@pytest.mark.django_db
def test_invalid_image_file_post(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:image-file-list",
        user=user,
        client=client,
        method=client.post,
        data={"upload_session": None, "filename": "dummy.bin"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "upload_session": ["This field may not be null."]
    }

    upload_session = RawImageUploadSessionFactory()
    response = get_view_for_user(
        viewname="api:image-file-list",
        user=user,
        client=client,
        method=client.post,
        data={"upload_session": upload_session.api_url, "filename": None},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {"filename": ["This field may not be null."]}


@pytest.mark.django_db
def test_empty_data_image_files(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        viewname="api:image-file-list",
        user=user,
        client=client,
        method=client.post,
        data={},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json() == {
        "filename": ["This field is required."],
        "upload_session": ["This field is required."],
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "is_staff, expected_response", [(False, 201), (True, 201)]
)
def test_image_file_post_permissions(client, is_staff, expected_response):
    upload_session = RawImageUploadSessionFactory()
    token = Token.objects.create(user=UserFactory(is_staff=is_staff))
    extra_headers = {"HTTP_AUTHORIZATION": f"Token {token}"}
    response = getattr(client, "post")(
        reverse("api:image-file-list"),
        data={
            "upload_session": upload_session.api_url,
            "filename": "dummy.bin",
        },
        **extra_headers,
    )
    assert response.status_code == expected_response
