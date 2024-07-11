from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.sessions.models import BrowserSession


@acks_late_micro_short_task
@transaction.atomic
def logout_privileged_users():
    BrowserSession.objects.filter(
        user__is_superuser=True,
        created__lt=now() - settings.SESSION_PRIVILEGED_USER_TIMEOUT,
    ).delete()
