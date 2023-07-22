from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"],
)
def update_verification_user_set(*, usernames):
    VerificationUserSet = apps.get_model(  # noqa: N806
        app_label="verifications", model_name="VerificationUserSet"
    )

    users = get_user_model().objects.filter(username__in=usernames)
    user_sets = VerificationUserSet.objects.filter(users__in=users)

    if not user_sets:
        user_sets = [VerificationUserSet.objects.create()]

    for user_set in user_sets:
        user_set.users.add(*users)
