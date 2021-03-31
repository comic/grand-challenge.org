import pytest

from tests.factories import UserFactory


@pytest.mark.django_db
def test_notification_preference_created():
    u = UserFactory()

    prefs = u.user_profile

    assert prefs
    assert prefs.user == u
    assert prefs.receive_notification_emails is True
    assert prefs.notification_email_last_sent_at is None
    assert prefs.has_notifications is False
    assert prefs.notifications_last_read_at is None
