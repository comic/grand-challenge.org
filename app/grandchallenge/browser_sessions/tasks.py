from django.conf import settings
from django.db import transaction
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.browser_sessions.models import BrowserSession
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task(name=f"{__name__}.logout_privileged_users")
@transaction.atomic
def logout_privileged_users_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return logout_privileged_users(**kwargs)


@lambda_task
def logout_privileged_users():
    BrowserSession.objects.filter(
        user__is_staff=True,
        created__lt=now() - settings.SESSION_PRIVILEGED_USER_TIMEOUT,
    ).only("pk").delete()


@acks_late_micro_short_task(name=f"{__name__}.clear_sessions")
@transaction.atomic
def clear_sessions_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return clear_sessions(**kwargs)


@lambda_task
def clear_sessions():
    BrowserSession.objects.filter(expire_date__lt=now()).only("pk").delete()
