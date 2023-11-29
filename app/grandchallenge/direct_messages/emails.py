from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q


def get_users_to_email():
    return (
        get_user_model()
        .objects.annotate(
            unread_message_count=Count(
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
        .filter(unread_message_count__gt=0)
    )
