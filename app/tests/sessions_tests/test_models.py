import pytest

from grandchallenge.sessions.models import BrowserSession
from tests.factories import UserFactory


@pytest.mark.django_db
def test_no_user_is_assigned_to_session(client):
    response = client.get("/")

    assert response.status_code == 200
    assert BrowserSession.objects.count() == 1
    assert BrowserSession.objects.get().user is None


@pytest.mark.django_db
def test_user_is_assigned_to_session_after_login(client):
    user = UserFactory()

    client.force_login(user)
    response = client.get("/")

    assert response.status_code == 200
    assert BrowserSession.objects.count() == 1
    assert BrowserSession.objects.first().user == user
