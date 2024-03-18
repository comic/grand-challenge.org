from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import Count, F, Q
from django.utils.timezone import now

from grandchallenge.notifications.emails import send_unread_notifications_email
from grandchallenge.profiles.models import (
    NotificationSubscriptionOptions,
    UserProfile,
)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_unread_notification_emails():
    site = Site.objects.get_current()

    profiles = (
        UserProfile.objects.filter(
            user__is_active=True,
            receive_notification_emails=NotificationSubscriptionOptions.DAILY_SUMMARY,
        )
        .annotate(
            unread_notification_count=Count(
                "user__notification__pk",
                filter=Q(user__notification__read=False)
                & (
                    Q(notification_email_last_sent_at__isnull=True)
                    | Q(
                        user__notification__created__gt=F(
                            "notification_email_last_sent_at"
                        )
                    )
                ),
                distinct=True,
            )
        )
        .filter(unread_notification_count__gt=0)
        .distinct()
        .select_related("user")
    )

    for profile in profiles.iterator():
        profile.notification_email_last_sent_at = now()
        profile.save(update_fields=["notification_email_last_sent_at"])

        send_unread_notifications_email(
            site=site,
            user=profile.user,
            n_notifications=profile.unread_notification_count,
        )
