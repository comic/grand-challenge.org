import pytest
from django.core import mail
from django.utils.timezone import now

from grandchallenge.notifications.models import Notification
from grandchallenge.notifications.tasks import send_unread_notification_emails
from grandchallenge.profiles.models import NotificationSubscriptionOptions
from tests.factories import UserFactory
from tests.notifications_tests.factories import NotificationFactory


@pytest.mark.django_db
def test_notification_email_last_sent_at_updated():
    user1 = UserFactory()
    _ = NotificationFactory(user=user1, type=Notification.Type.GENERIC)
    assert not user1.user_profile.notification_email_last_sent_at
    send_unread_notification_emails()
    user1.refresh_from_db()
    assert user1.user_profile.notification_email_last_sent_at


@pytest.mark.django_db
def test_daily_notification_email_only_about_new_unread_notifications():
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


@pytest.mark.django_db
def test_daily_notification_email_opt_in():
    inactive_user, user_no_email, user_instant_email, user_daily_email = (
        UserFactory.create_batch(4)
    )

    inactive_user.is_active = False
    inactive_user.save()

    user_no_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.DISABLED
    )
    user_no_email.user_profile.save()

    user_instant_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.INSTANT
    )
    user_instant_email.user_profile.save()

    user_daily_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.DAILY_SUMMARY
    )
    user_daily_email.user_profile.save()

    _ = NotificationFactory(user=inactive_user, type=Notification.Type.GENERIC)
    _ = NotificationFactory(user=user_no_email, type=Notification.Type.GENERIC)
    _ = NotificationFactory(
        user=user_instant_email, type=Notification.Type.GENERIC
    )
    _ = NotificationFactory(
        user=user_daily_email, type=Notification.Type.GENERIC
    )

    send_unread_notification_emails()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user_daily_email.email]


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


@pytest.mark.django_db
def test_instant_email_notification_opt_in():
    inactive_user, user_no_email, user_instant_email, user_daily_email = (
        UserFactory.create_batch(4)
    )

    inactive_user.is_active = False
    inactive_user.save()

    user_no_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.DISABLED
    )
    user_no_email.user_profile.save()

    user_instant_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.INSTANT
    )
    user_instant_email.user_profile.save()

    user_daily_email.user_profile.receive_notification_emails = (
        NotificationSubscriptionOptions.DAILY_SUMMARY
    )
    user_daily_email.user_profile.save()

    Notification.send(
        kind=Notification.Type.FILE_COPY_STATUS, actor=inactive_user
    )
    Notification.send(
        kind=Notification.Type.FILE_COPY_STATUS, actor=user_no_email
    )
    Notification.send(
        kind=Notification.Type.FILE_COPY_STATUS, actor=user_instant_email
    )
    Notification.send(
        kind=Notification.Type.FILE_COPY_STATUS, actor=user_daily_email
    )

    # only the user with instant notification emails enabled gets an email
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user_instant_email.email]
