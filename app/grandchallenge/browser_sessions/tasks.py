from django.conf import settings
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.browser_sessions.models import BrowserSession


@lambda_task
def logout_privileged_users():
    BrowserSession.objects.filter(
        user__is_staff=True,
        created__lt=now() - settings.SESSION_PRIVILEGED_USER_TIMEOUT,
    ).only("pk").delete()


@lambda_task
def clear_sessions():
    BrowserSession.objects.filter(expire_date__lt=now()).only("pk").delete()
