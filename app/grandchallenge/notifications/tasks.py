from celery import shared_task
from django.core.paginator import Paginator
from django.utils.timezone import now

from grandchallenge.notifications.emails import send_unread_notifications_email
from grandchallenge.profiles.models import UserProfile


@shared_task
def send_unread_notification_emails():
    profiles = (
        UserProfile.objects.filter(
            receive_notification_emails=True, user__notification__read=False,
        )
        .distinct()
        .prefetch_related("user__notification_set")
        .order_by("pk")
    )
    paginator = Paginator(profiles, 1000)

    for page_nr in paginator.page_range:
        current_page_profiles = paginator.page(page_nr).object_list
        current_time = now()
        recipients = {}
        for profile in current_page_profiles:
            unread_notifications = [
                n
                for n in profile.user.notification_set.all()
                if not n.read
                and (
                    profile.notification_email_last_sent_at is None
                    or n.created > profile.notification_email_last_sent_at
                )
            ]
            if unread_notifications:
                recipients[profile] = len(unread_notifications)
                profile.notification_email_last_sent_at = current_time

        UserProfile.objects.bulk_update(
            current_page_profiles, ["notification_email_last_sent_at"]
        )
        send_unread_notifications_email(recipients)
