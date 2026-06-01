from django.contrib.auth import get_user_model
from lambda_tasks.decorators import lambda_task

from grandchallenge.core.celery import acks_late_micro_short_task


@acks_late_micro_short_task(name=f"{__name__}.update_verification_user_set")
def update_verification_user_set_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return update_verification_user_set(**kwargs)


@lambda_task
def update_verification_user_set(*, usernames: list[str]):
    from grandchallenge.verifications.models import VerificationUserSet

    users = get_user_model().objects.filter(username__in=usernames)
    user_sets = VerificationUserSet.objects.filter(users__in=users)

    if not user_sets:
        user_sets = [VerificationUserSet.objects.create()]

    for user_set in user_sets:
        user_set.users.add(*users)
