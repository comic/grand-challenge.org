import pytest
from actstream.actions import follow

from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import NotificationSubscriptionOptions
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_notification_preference_created():
    u = UserFactory()

    prefs = u.user_profile

    assert prefs
    assert prefs.user == u
    assert (
        prefs.receive_notification_emails
        is NotificationSubscriptionOptions.DAILY_SUMMARY
    )
    assert prefs.notification_email_last_sent_at is None
    assert prefs.has_unread_notifications is False


@pytest.mark.django_db
def test_notifications_filtered():
    u1 = UserFactory()
    u2 = UserFactory()

    follow(u1, u2)

    n = NotificationFactory(
        user=u1, type=Notification.Type.GENERIC, actor=u1, message="says hi"
    )

    assert u2.user_profile.has_unread_notifications is False
    assert u1.user_profile.has_unread_notifications is True

    n.read = True
    n.save()

    assert u1.user_profile.has_unread_notifications is False


@pytest.mark.django_db
def test_submit_newsletter_preference(client):
    u1 = UserFactory()
    u2 = UserFactory()

    assert u1.user_profile.receive_newsletter is None
    assert u2.user_profile.receive_newsletter is None

    response = get_view_for_user(
        viewname="newsletter-sign-up",
        client=client,
        method=client.post,
        data={"receive_newsletter": True},
        reverse_kwargs={"username": u1.username},
        user=u1,
    )
    assert response.status_code == 302
    u1.user_profile.refresh_from_db()
    assert u1.user_profile.receive_newsletter

    response = get_view_for_user(
        viewname="newsletter-sign-up",
        client=client,
        method=client.post,
        data={"receive_newsletter": True},
        reverse_kwargs={"username": u1.username},
        user=u2,
    )
    assert response.status_code == 403
