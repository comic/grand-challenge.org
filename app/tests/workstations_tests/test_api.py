import pytest

from tests.factories import UserFactory, SessionFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_session_list_api(client):
    user = UserFactory(is_staff=True)

    response = get_view_for_user(
        client=client,
        viewname="api:session-list",
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0

    s, _ = SessionFactory(), SessionFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:session-list",
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_session_detail_api(client):
    user = UserFactory(is_staff=True)
    s = SessionFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:session-detail",
        reverse_kwargs={"pk": s.pk},
        user=user,
        content_type="application/json",
    )

    # Status and pk are required by the js app
    assert response.status_code == 200
    assert all([k in response.json() for k in ["pk", "status"]])
    assert response.json()["pk"] == str(s.pk)
    assert response.json()["status"] == s.get_status_display()


@pytest.mark.django_db
def test_session_api_permissions(client):
    tests = [(UserFactory(), 403), (UserFactory(is_staff=True), 200)]
    session = SessionFactory()

    for test in tests:
        response = get_view_for_user(
            client=client,
            viewname="api:session-list",
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]

        response = get_view_for_user(
            client=client,
            viewname="api:session-detail",
            reverse_kwargs={"pk": session.pk},
            user=test[0],
            content_type="application/json",
        )
        assert response.status_code == test[1]
