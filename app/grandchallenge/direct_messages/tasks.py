from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.db.models import Count, F, Q

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.profiles.models import NotificationEmailOptions


def get_users_to_send_new_unread_direct_messages_email():
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


@acks_late_micro_short_task
def send_new_unread_direct_messages_emails():
    site = Site.objects.get_current()

    for user in get_users_to_send_new_unread_direct_messages_email().iterator(
        chunk_size=100
    ):
        user.user_profile.dispatch_unread_direct_messages_email(
            site=site,
            new_unread_message_count=user.new_unread_message_count,
            new_senders=get_new_senders(user=user),
        )
