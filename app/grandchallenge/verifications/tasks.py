from django.apps import apps
from django.contrib.auth import get_user_model

from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task
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
