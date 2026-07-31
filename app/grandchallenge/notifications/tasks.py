from django.contrib.sites.models import Site
from lambda_tasks.decorators import lambda_task

from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.profiles.models import (
    NotificationEmailOptions,
    UserProfile,
)


@lambda_task
def send_unread_notification_emails():
    site = Site.objects.get_current()

    profiles = (
        UserProfile.objects.filter(
            notification_email_choice=NotificationEmailOptions.DAILY_SUMMARY,
            user__is_active=True,
        )
        .with_unread_notifications()
        .select_related("user")
    )

    for profile in profiles.iterator():
        profile.dispatch_unread_notifications_email(
            site=site,
            unread_notification_count=profile.unread_notification_count,
        )


@lambda_task(retry_on=(LockNotAcquiredException,))
def send_unread_notification_instant_emails(*, user_profile_ids: list[int]):
    site = Site.objects.get_current()

    with check_lock_acquired():
        len(
            UserProfile.objects.select_for_update(nowait=True)
            .filter(pk__in=user_profile_ids)
            .values_list("pk", flat=True)
        )

    profiles = (
        UserProfile.objects.filter(
            pk__in=user_profile_ids,
            notification_email_choice=NotificationEmailOptions.INSTANT,
            user__is_active=True,
        )
        .with_unread_notifications()
        .select_related("user")
    )

    for profile in profiles.iterator():
        profile.dispatch_unread_notifications_email(
            site=site,
            unread_notification_count=profile.unread_notification_count,
        )
