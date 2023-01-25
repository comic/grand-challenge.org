from datetime import timedelta
from pathlib import Path

import pytest
from django.utils.timezone import now

from grandchallenge.workstations.models import Feedback
from tests.cases_tests import RESOURCE_PATH
from tests.factories import SessionFactory, UserFactory, WorkstationFactory
from tests.utils import get_view_for_user
from tests.workstations_tests.factories import FeedbackFactory


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
def test_session_only_patchable_by_creator(client):
    user = UserFactory()
    s = SessionFactory(creator=user)

    assert s.maximum_duration == timedelta(minutes=10)

    response = get_view_for_user(
        client=client,
        method=client.patch,
        viewname="api:session-keep-alive",
        reverse_kwargs={"pk": s.pk},
        user=UserFactory(),
        content_type="application/json",
    )

    assert response.status_code == 404


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


@pytest.mark.django_db
def test_session_feedback_api_view_permissions(client):
    user1, user2 = UserFactory.create_batch(2)
    session = SessionFactory(creator=user1)
    feedback = FeedbackFactory(session=session)
    assert user1.has_perm("view_feedback", feedback)

    response = get_view_for_user(
        viewname="api:workstations-feedback-detail",
        reverse_kwargs={"pk": feedback.pk},
        client=client,
        user=user1,
        follow=True,
    )
    assert response.status_code == 200

    response = get_view_for_user(
        viewname="api:workstations-feedback-detail",
        reverse_kwargs={"pk": feedback.pk},
        client=client,
        user=user2,
        follow=True,
    )
    assert response.status_code == 404

    response = get_view_for_user(
        viewname="api:workstations-feedback-list",
        client=client,
        user=user1,
        follow=True,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = get_view_for_user(
        viewname="api:workstations-feedback-list",
        client=client,
        user=user2,
        follow=True,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_create_session_feedback(client):
    user = UserFactory()
    session = SessionFactory(creator=user)

    with open(Path(RESOURCE_PATH / "test_grayscale.jpg"), "rb") as file:
        response = get_view_for_user(
            viewname="api:workstations-feedback-list",
            client=client,
            method=client.post,
            data={
                "session": session.api_url,
                "user_comment": "Some comment",
                "screenshot": file,
                "context": '{"foo": "bar"}',
            },
            user=user,
            follow=True,
        )

    assert response.status_code == 201
    assert Feedback.objects.count() == 1
    feedback = Feedback.objects.get()
    assert feedback.session == session
    assert feedback.user_comment == "Some comment"
    assert feedback.context == {"foo": "bar"}
    assert "test_grayscale.jpg" in feedback.screenshot.name


@pytest.mark.django_db
def test_only_session_creator_can_create_session_feedback(client):
    user1, user2 = UserFactory.create_batch(2)
    session = SessionFactory(creator=user1)

    response = get_view_for_user(
        viewname="api:workstations-feedback-list",
        client=client,
        method=client.post,
        data={"session": session.api_url, "user_comment": "Some comment"},
        user=user2,
        follow=True,
    )
    assert response.status_code == 400
    assert response.json() == {
        "session": ["Invalid hyperlink - Object does not exist."]
    }
    assert Feedback.objects.count() == 0

    response = get_view_for_user(
        viewname="api:workstations-feedback-list",
        client=client,
        method=client.post,
        data={"session": session.api_url, "user_comment": "Some comment"},
        user=user1,
        follow=True,
    )
    assert response.status_code == 201
    assert Feedback.objects.count() == 1


@pytest.mark.django_db
def test_workstation_api(client):
    user = UserFactory()

    response = get_view_for_user(
        client=client,
        viewname="api:workstations-list",
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1

    ws1, _ = WorkstationFactory(), WorkstationFactory()
    ws1.add_user(user)

    response = get_view_for_user(
        client=client,
        viewname="api:workstations-list",
        user=user,
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["count"] == 2
