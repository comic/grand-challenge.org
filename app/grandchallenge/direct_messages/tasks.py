from celery import shared_task
from django.conf import settings
from django.contrib.sites.models import Site

from grandchallenge.direct_messages.emails import (
    get_users_to_send_new_unread_direct_messages_email,
)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def send_new_unread_direct_messages_emails():
    site = Site.objects.get_current()
    for user in get_users_to_send_new_unread_direct_messages_email().iterator(
        chunk_size=100
    ):
        user.user_profile.dispatch_unread_direct_messages_email(site=site)
