import pytest

from grandchallenge.cases.models import RawImageUploadSession
from tests.algorithms_tests.factories import AlgorithmImageFactory
from tests.cases_tests.factories import RawImageUploadSessionFactory
from tests.factories import UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_upload_session_list(client):
    upload_session_1, _ = (
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
