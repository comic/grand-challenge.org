from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db.models import Count, F, Q


def get_users_to_send_new_unread_direct_messages_email():
    # local import to avoid circular dependency
    from grandchallenge.profiles.models import NotificationEmailOptions

    return (
        get_user_model()
        .objects.prefetch_related(
            "unread_direct_messages__sender", "user_profile"
        )
        .filter(
            user_profile__notification_email_choice=NotificationEmailOptions.DAILY_SUMMARY,
            is_active=True,
        )
        .annotate(
            new_unread_message_count=Count(
                "unread_direct_messages",
                filter=Q(
                    user_profile__unread_messages_email_last_sent_at__isnull=True
                )
                | Q(
                    unread_direct_messages__created__gt=F(
                        "user_profile__unread_messages_email_last_sent_at"
                    )
                ),
            )
        )
        .filter(new_unread_message_count__gt=0)
    )


def get_new_senders(*, user):
    new_senders = {
        message.sender
        for message in user.unread_direct_messages.all()
        if (
            user.user_profile.unread_messages_email_last_sent_at is None
            or message.created
            > user.user_profile.unread_messages_email_last_sent_at
        )
    }
    return sorted(list(new_senders), key=lambda s: s.pk)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_new_unread_direct_messages_emails():
    site = Site.objects.get_current()
    for user in get_users_to_send_new_unread_direct_messages_email().iterator(
        chunk_size=100
    ):
        user.user_profile.dispatch_unread_direct_messages_email(site=site)
