import pytest
from actstream import action
from actstream.actions import follow

from grandchallenge.notifications.models import Notification
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


@pytest.mark.django_db
def test_notifications_filtered():
    u1 = UserFactory()
    u2 = UserFactory()

    follow(u1, u2)

    action.send(sender=u2, verb="says hi")

    assert u2.user_profile.has_unread_notifications is False
    assert u1.user_profile.has_unread_notifications is True

    n = Notification.objects.filter(user=u1).get()
    n.read = True
    n.save()

    assert u1.user_profile.has_unread_notifications is False
    assert str(u1.notification_set.get().action).startswith(f"{u2} says hi")
