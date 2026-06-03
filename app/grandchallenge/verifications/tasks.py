from django.contrib.auth import get_user_model
from lambda_tasks.decorators import lambda_task


@lambda_task
def update_verification_user_set(*, usernames: list[str]):
    from grandchallenge.verifications.models import VerificationUserSet

    users = get_user_model().objects.filter(username__in=usernames)
    user_sets = VerificationUserSet.objects.filter(users__in=users)

    if not user_sets:
        user_sets = [VerificationUserSet.objects.create()]

    for user_set in user_sets:
        user_set.users.add(*users)
