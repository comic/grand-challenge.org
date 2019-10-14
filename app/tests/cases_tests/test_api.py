import pytest
from tests.utils import get_view_for_user
from tests.factories import UserFactory
from tests.cases_tests.factories import (
    RawImageUploadSessionFactory,
    RawImageFileFactory,
)
from tests.algorithms_tests.factories import AlgorithmImageFactory

from grandchallenge.cases.models import RawImageUploadSession, RawImageFile


@pytest.mark.django_db
def test_upload_session_list(client):
    upload_session_1, upload_session_2 = (
        RawImageUploadSessionFactory(),
        RawImageUploadSessionFactory(),
    )

    user = UserFactory(is_staff=True)
    response = get_view_for_user(
        viewname="api:upload-session-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        viewname="api:upload-session-detail",
        reverse_kwargs={"pk": upload_session_1.pk},
        user=user,
        client=client,
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
    "is_staff, expected_response", [(False, 403), (True, 201)]
)
def test_upload_session_post_permissions(client, is_staff, expected_response):
    user = UserFactory(is_staff=is_staff)
    algo = AlgorithmImageFactory()
    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"algorithm_image": algo.api_url},
        content_type="application/json",
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_image_file_list(client):
    file_list_1, file_list_2 = (RawImageFileFactory(), RawImageFileFactory())

    user = UserFactory(is_staff=True)
    response = get_view_for_user(
        viewname="api:image-file-list", user=user, client=client
    )
    assert response.status_code == 200
    assert response.json()["count"] == 2

    response = get_view_for_user(
        viewname="api:image-file-detail",
        reverse_kwargs={"pk": file_list_1.pk},
        user=user,
        client=client,
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
    "is_staff, expected_response", [(False, 403), (True, 201)]
)
def test_image_file_post_permissions(client, is_staff, expected_response):
    user = UserFactory(is_staff=is_staff)
    upload_session = RawImageUploadSessionFactory()
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
    assert response.status_code == expected_response
