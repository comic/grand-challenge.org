from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.timezone import now

from grandchallenge.direct_messages.emails import (
    get_new_senders,
    get_users_to_send_new_unread_direct_messages_email,
    send_new_unread_direct_messages_email,
)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_new_unread_direct_messages_emails():
    site = Site.objects.get_current()

    for user in get_users_to_send_new_unread_direct_messages_email().iterator(
        chunk_size=100
    ):
        new_senders = [s.first_name for s in get_new_senders(user=user)]

        user.user_profile.unread_messages_email_last_sent_at = now()
        user.user_profile.save(
            update_fields=["unread_messages_email_last_sent_at"]
        )

        send_new_unread_direct_messages_email(
            site=site,
            username=user.username,
            email=user.email,
            new_senders=new_senders,
            new_unread_message_count=user.new_unread_message_count,
        )
