import pytest
from actstream import action
from actstream.actions import follow
from django.utils.timezone import now

from tests.factories import UserFactory


@pytest.mark.django_db
def test_notification_preference_created():
    u = UserFactory()

    prefs = u.user_profile

    assert prefs
    assert prefs.user == u
    assert prefs.receive_notification_emails is True
    assert prefs.notification_email_last_sent_at is None
    assert prefs.has_unread_notifications is False
    assert prefs.notifications_last_read_at is None


@pytest.mark.django_db
def test_notifications_filtered():
    u1 = UserFactory()
    u2 = UserFactory()

    follow(u1, u2)

    action.send(sender=u2, verb="says hi")

    assert u2.user_profile.has_unread_notifications is False
    assert u1.user_profile.has_unread_notifications is True

    u1.user_profile.notifications_last_read_at = now()
    u1.user_profile.save()

    assert u1.user_profile.has_unread_notifications is False
    assert str(u1.user_profile.notifications.get()).startswith(f"{u2} says hi")
