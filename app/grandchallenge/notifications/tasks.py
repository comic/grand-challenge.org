from celery import shared_task
from django.db.models import Q
from django.utils.timezone import now

from grandchallenge.notifications.emails import send_unread_notifications_email
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import UserProfile


@shared_task
def send_unread_notification_emails():
    users = UserProfile.objects.filter(receive_notification_emails=True)
    recipients = {}
    for user in users:
        if (
            user.notification_email_last_sent_at is None
            and user.has_unread_notifications
        ):
            recipients[user] = len(user.unread_notifications)
            user.notification_email_last_sent_at = now()
            user.save()
        elif user.notification_email_last_sent_at is not None:
            unread_notifications = Notification.objects.filter(
                Q(user=user.user)
                & Q(read=False)
                & Q(action__timestamp__gt=user.notification_email_last_sent_at)
            )
            if unread_notifications:
                recipients[user] = len(unread_notifications)
                user.notification_email_last_sent_at = now()
                user.save()

    send_unread_notifications_email(recipients)
