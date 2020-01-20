import pytest

from grandchallenge.cases.models import RawImageFile, RawImageUploadSession
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.cases_tests.factories import (
    RawImageFileFactory,
    RawImageUploadSessionFactory,
)
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_session_list(client):
    u1, u2 = UserFactory(), UserFactory()
    RawImageUploadSessionFactory(creator=u1)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        client=client,
        user=u1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:upload-session-list",
        client=client,
        user=u2,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_upload_session_detail(client):
    u1, u2 = UserFactory(), UserFactory()
    us = RawImageUploadSessionFactory(creator=u1)

    response = get_view_for_user(
        viewname="api:upload-session-detail",
        reverse_kwargs={"pk": us.pk},
        client=client,
        user=u1,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:upload-session-detail",
        reverse_kwargs={"pk": us.pk},
        client=client,
        user=u2,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_upload_sessions_create(client):
    user = UserFactory()
    ai = AlgorithmImageFactory()
    ai.algorithm.add_user(user)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"algorithm_image": ai.api_url},
        content_type="application/json",
    )
    assert response.status_code == 201

    upload_session = RawImageUploadSession.objects.get(
        pk=response.data.get("pk")
    )
    assert upload_session.algorithm_image == ai


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
    "is_active, expected_response", [(False, 401), (True, 201)]
)
def test_upload_session_post_permissions(client, is_active, expected_response):
    user = UserFactory(is_active=is_active)
    ai = AlgorithmImageFactory()
    ai.algorithm.add_user(user)

    response = get_view_for_user(
        viewname="api:upload-session-list",
        user=user,
        client=client,
        method=client.post,
        data={"algorithm_image": ai.api_url},
        content_type="application/json",
    )
    assert response.status_code == expected_response


@pytest.mark.django_db
def test_image_file_list(client):
    u1, u2 = UserFactory(), UserFactory()
    us1 = RawImageUploadSessionFactory(creator=u1)
    RawImageFileFactory(upload_session=us1)

    response = get_view_for_user(
        viewname="api:image-file-list",
        client=client,
        user=u1,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:image-file-list",
        client=client,
        user=u2,
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_image_file_detail(client):
    u1, u2 = UserFactory(), UserFactory()
    us = RawImageUploadSessionFactory(creator=u1)
    rif = RawImageFileFactory(upload_session=us)

    response = get_view_for_user(
        viewname="api:image-file-detail",
        reverse_kwargs={"pk": rif.pk},
        client=client,
        user=u1,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:image-file-detail",
        reverse_kwargs={"pk": rif.pk},
        client=client,
        user=u2,
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_image_file_create(client):
    user = UserFactory(is_staff=True)
    ai = AlgorithmImageFactory()
    ai.algorithm.add_user(user)
    upload_session = RawImageUploadSessionFactory(
        creator=user, algorithm_image=ai
    )

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
    assert response.status_code == 400


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
    "is_active, expected_response", [(False, 401), (True, 201)]
)
def test_image_file_post_permissions(client, is_active, expected_response):
    user = UserFactory(is_active=is_active)
    algo = AlgorithmImageFactory(creator=user)
    upload_session = RawImageUploadSessionFactory(
        creator=user, algorithm_image=algo
    )
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


@pytest.mark.django_db
def test_process_images_api_view(client, settings):
    # Override the celery settings
    settings.task_eager_propagates = (True,)
    settings.task_always_eager = (True,)

    user = UserFactory()
    us = RawImageUploadSessionFactory(creator=user)
    RawImageFileFactory(upload_session=us)

    def request_processing():
        return get_view_for_user(
            viewname="api:upload-session-process-images",
            reverse_kwargs={"pk": us.pk},
            user=user,
            client=client,
            method=client.patch,
            content_type="application/json",
        )

    # First request should work
    response = request_processing()
    assert response.status_code == 200

    # Jobs should only be run once
    response = request_processing()
    assert response.status_code == 400
