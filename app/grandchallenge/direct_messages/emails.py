from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q


def get_users_to_send_new_unread_direct_messages_email():
    return (
        get_user_model()
        .objects.prefetch_related(
            "unread_direct_messages__sender", "user_profile"
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
    return {
        message.sender
        for message in user.unread_direct_messages.all()
        if (
            user.user_profile.unread_messages_email_last_sent_at is None
            or message.created
            > user.user_profile.unread_messages_email_last_sent_at
        )
    }
