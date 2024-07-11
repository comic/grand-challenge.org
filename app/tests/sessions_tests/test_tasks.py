from datetime import timedelta

import pytest
from django.test import Client
from django.utils.timezone import now

from grandchallenge.sessions.tasks import logout_privileged_users
from tests.factories import UserFactory


@pytest.mark.django_db
def test_logout_privileged_users(settings):
    settings.SESSION_PRIVILEGED_USER_TIMEOUT = timedelta(hours=1)

    # Unprivileged user, stays logged in
    u1 = UserFactory()
    # Privileged user, new session, stays logged in
    u2 = UserFactory(is_superuser=True)
    # Privileged user, old session, should be logged out
    u3 = UserFactory(is_superuser=True)

    # Create sessions for each user, note that
    # separate clients are used to simulate different users
    # otherwise the session is deleted when the 2nd logs in
    Client().force_login(u1)
    Client().force_login(u2)
    Client().force_login(u3)

    assert u1.browser_sessions.count() == 1
    assert u2.browser_sessions.count() == 1
    assert u3.browser_sessions.count() == 1

    session = u3.browser_sessions.get()
    session.created = now() - timedelta(hours=2)
    session.save()

    logout_privileged_users()

    u1.refresh_from_db()
    u2.refresh_from_db()
    u3.refresh_from_db()

    assert u1.is_active is True
    assert u2.is_active is True
    assert u3.is_active is True
    assert u1.browser_sessions.count() == 1
    assert u2.browser_sessions.count() == 1
    assert u3.browser_sessions.count() == 0
