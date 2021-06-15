from celery import shared_task
from django.core.paginator import Paginator
from django.utils.timezone import now

from grandchallenge.notifications.emails import send_unread_notifications_email
from grandchallenge.notifications.models import Notification
from grandchallenge.profiles.models import UserProfile


@shared_task
def send_unread_notification_emails():
    profiles = UserProfile.objects.filter(
        receive_notification_emails=True
    ).order_by("user")
    paginator = Paginator(profiles, 1000)

    for page_nr in paginator.page_range:
        current_page_profiles = paginator.page(page_nr).object_list
        current_time = now()
        recipients = {}
        for profile in current_page_profiles:
            if (
                profile.notification_email_last_sent_at is None
                and profile.has_unread_notifications
            ):
                recipients[profile] = profile.unread_notifications.count()
                profile.notification_email_last_sent_at = current_time
                profile.save()
            elif profile.notification_email_last_sent_at is not None:
                unread_notifications = Notification.objects.filter(
                    user=profile.user,
                    read=False,
                    action__timestamp__gt=profile.notification_email_last_sent_at,
                ).count()
                if unread_notifications:
                    recipients[profile] = unread_notifications
                    profile.notification_email_last_sent_at = current_time
                    profile.save()

        send_unread_notifications_email(recipients)
