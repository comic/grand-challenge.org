from celery import shared_task
from django.utils.timezone import now

from grandchallenge.notifications.emails import send_unread_notifications_email
from grandchallenge.profiles.models import UserProfile


@shared_task
def send_unread_notification_emails():
    users = UserProfile.objects.filter(receive_notification_emails=True)
    recipients = {}
    for user in users:
        if user.has_unread_notifications:
            recipients[user] = len(user.unread_notifications)
            user.notification_email_last_sent_at = now()
            user.save()

    send_unread_notifications_email(recipients)
