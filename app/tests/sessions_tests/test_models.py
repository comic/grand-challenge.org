import pytest

from grandchallenge.browser_sessions.models import BrowserSession
from tests.factories import UserFactory


@pytest.mark.django_db
def test_no_user_is_assigned_to_session(client):
    existing_browser_sessions = list(
        BrowserSession.objects.values_list("pk", flat=True)
    )
    # no session for anonymous user
    response = client.get("/")
    new_browser_sessions = BrowserSession.objects.exclude(
        pk__in=existing_browser_sessions
    )

    assert response.status_code == 200
    assert new_browser_sessions.count() == 0


@pytest.mark.django_db
def test_user_is_assigned_to_session_after_login(client):
    existing_browser_sessions = list(
        BrowserSession.objects.values_list("pk", flat=True)
    )
    user = UserFactory()

    client.force_login(user)
    response = client.get("/")
    new_browser_sessions = BrowserSession.objects.exclude(
        pk__in=existing_browser_sessions
    )

    assert response.status_code == 200
    assert new_browser_sessions.count() == 1
    assert new_browser_sessions.first().user == user
