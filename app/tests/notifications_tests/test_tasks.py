import pytest
from django.core import mail
from django.utils.timezone import now

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.tasks import send_unread_notification_emails
from grandchallenge.profiles.models import NotificationSubscriptionOptions
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory


@pytest.mark.parametrize(
    "notification_preference, num_emails",
    [
        (NotificationSubscriptionOptions.DAILY_SUMMARY, 1),
        (NotificationSubscriptionOptions.INSTANT, 1),
        (NotificationSubscriptionOptions.DISABLED, 0),
    ],
)
@pytest.mark.django_db
def test_notification_email(notification_preference, num_emails):
    user1, user2 = UserFactory.create_batch(2)
    user1.is_active = False
    user1.save()
    for user in [user1, user2]:
        user.user_profile.receive_notification_emails = notification_preference
        user.user_profile.save()
        _ = NotificationFactory(user=user, type=Notification.Type.GENERIC)
        assert user.user_profile.has_unread_notifications

    assert len(mail.outbox) == 0

    send_unread_notification_emails()
    assert len(mail.outbox) == num_emails
    for email in mail.outbox:
        assert user2.email in email.to
        assert user1.email not in email.to
        assert "You have 1 new notification" in str(email.body)


@pytest.mark.django_db
def test_notification_email_last_sent_at_updated():
    user1 = UserFactory()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    assert not user1.user_profile.notification_email_last_sent_at
    send_unread_notification_emails()
    user1.refresh_from_db()
    assert user1.user_profile.notification_email_last_sent_at


@pytest.mark.django_db
def test_notification_email_only_about_new_unread_notifications():
    user1 = UserFactory()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)

    # mimic sending notification email by updating time stamp
    user1.user_profile.notification_email_last_sent_at = now()
    user1.user_profile.save()

    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    send_unread_notification_emails()

    # user has 2 unread notifications
    assert len(user1.user_profile.unread_notifications) == 2
    # but only receives an email about unread notifications since the last email
    assert mail.outbox[-1].to[0] == user1.email
    assert "You have 1 new notification" in mail.outbox[-1].body


@pytest.mark.parametrize(
    "preference,num_emails",
    [
        (NotificationSubscriptionOptions.DAILY_SUMMARY, 1),
        (NotificationSubscriptionOptions.INSTANT, 1),
        (NotificationSubscriptionOptions.DISABLED, 0),
    ],
)
@pytest.mark.django_db
def test_notification_email_opt_out(preference, num_emails):
    user1 = UserFactory()
    user1.user_profile.receive_notification_emails = preference
    user1.user_profile.save()

    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)

    send_unread_notification_emails()
    assert len(mail.outbox) == num_emails


@pytest.mark.django_db
def test_notification_email_counts():
    user1, user2, user3 = UserFactory.create_batch(3)
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user2, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user2, type=Notification.Type.GENERIC)

    assert len(mail.outbox) == 0
    send_unread_notification_emails()
    assert len(mail.outbox) == 2

    assert mail.outbox[0].to[0] == user1.email
    assert "You have 1 new notification" in mail.outbox[0].body

    assert mail.outbox[1].to[0] == user2.email
    assert "You have 2 new notifications" in mail.outbox[1].body

    send_unread_notification_emails()
    assert len(mail.outbox) == 2
