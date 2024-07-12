from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.browser_sessions.models import BrowserSession
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task
@transaction.atomic
def logout_privileged_users():
    BrowserSession.objects.filter(
        user__is_staff=True,
        created__lt=now() - settings.SESSION_PRIVILEGED_USER_TIMEOUT,
    ).delete()


@acks_late_micro_short_task
@transaction.atomic
def clear_sessions():
    BrowserSession.objects.filter(expire_date__lt=now()).delete()
