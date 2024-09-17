from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.browser_sessions.models import BrowserSession
from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task
@transaction.atomic
def deactivate_user(*, user_pk):
    user = (
        get_user_model().objects.select_related("verification").get(pk=user_pk)
    )

    user.is_active = False
    user.save()

    try:
        user.verification.is_verified = False
        user.verification.save()
    except ObjectDoesNotExist:
        # No verification, no problem
        pass

    BrowserSession.objects.filter(user=user).delete()


@acks_late_micro_short_task
@transaction.atomic
def delete_users_who_dont_login():
    """Remove users who do not sign in after USER_LOGIN_TIMEOUT_DAYS"""
    get_user_model().objects.exclude(
        username=settings.ANONYMOUS_USER_NAME
    ).filter(
        last_login__isnull=True,
        date_joined__lt=(
            now() - timedelta(days=settings.USER_LOGIN_TIMEOUT_DAYS)
        ),
    ).only(
        "pk"
    ).delete()
