from datetime import timedelta

import pytest
from django.utils.timezone import now

from tests.factories import SessionFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_session_list_api(client):
    user = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:session-list",
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0

    _ = SessionFactory(creator=user), SessionFactory(creator=user)

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
    user = UserFactory()
    s = SessionFactory(creator=user)

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
def test_session_update_read_only_fails(client):
    user = UserFactory()
    s = SessionFactory(creator=user)

    response = get_view_for_user(
        client=client,
        method=client.patch,
        viewname="api:session-keep-alive",
        reverse_kwargs={"pk": s.pk},
        user=user,
        data={"status": "Stopped"},
        content_type="application/json",
    )

    assert response.status_code == 200

    s.refresh_from_db()
    assert s.status == s.QUEUED


@pytest.mark.django_db
def test_session_update_extends_timeout(client):
    user = UserFactory()
    s = SessionFactory(creator=user)

    assert s.maximum_duration == timedelta(minutes=10)

    response = get_view_for_user(
        client=client,
        method=client.patch,
        viewname="api:session-keep-alive",
        reverse_kwargs={"pk": s.pk},
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200

    s.refresh_from_db()
    # Just check that it changed from the default
    assert s.maximum_duration != timedelta(minutes=10)


@pytest.mark.django_db
def test_session_keep_alive_limit(client, settings):
    user = UserFactory()
    s = SessionFactory(creator=user)

    assert s.maximum_duration == timedelta(minutes=10)

    s.created = now() - timedelta(days=1)
    s.save()

    response = get_view_for_user(
        client=client,
        method=client.patch,
        viewname="api:session-keep-alive",
        reverse_kwargs={"pk": s.pk},
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 400

    s.refresh_from_db()
    assert s.maximum_duration == timedelta(
        seconds=settings.WORKSTATIONS_SESSION_DURATION_LIMIT
    )
