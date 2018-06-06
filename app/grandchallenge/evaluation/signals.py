from typing import Union

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from grandchallenge.evaluation.emails import send_new_result_email
from grandchallenge.evaluation.models import (
    Submission, Job, Method, Result, Config,
)
from grandchallenge.evaluation.tasks import (
    evaluate_submission, calculate_ranks
)


@receiver(post_save, sender=Submission)
def create_evaluation_job(
    instance: Submission = None, created: bool = False, *_, **__
):
    if created:
        method = Method.objects.filter(challenge=instance.challenge).order_by(
            '-created'
        ).first()
        if method is None:
            # TODO: Email here, do not raise
            # raise NoMethodForChallengeError
            pass
        else:
            Job.objects.create(submission=instance, method=method)


@receiver(post_save, sender=Job)
def execute_job(instance: Job = None, created: bool = False, *_, **__):
    if created:
        # TODO: Create Timeout tests
        evaluate_submission.apply_async(
            task_id=str(instance.pk), kwargs={'job_pk': instance.pk}
        )


@receiver(post_save, sender=Config)
@receiver(post_save, sender=Result)
def recalculate_ranks(instance: Union[Result, Config] = None, *_, **__):
    """Recalculates the ranking on a new result"""
    calculate_ranks.apply_async(kwargs={'challenge_pk': instance.challenge.pk})


@receiver(post_save, sender=Result)
def cache_absolute_url(instance: Result = None, *_, **__):
    """Cache the absolute url to speed up the results page, needs the pk of
    the result so cannot so into a custom save method"""
    Result.objects.filter(pk=instance.pk).update(
        absolute_url=instance.get_absolute_url()
    )


@receiver(post_save, sender=Result)
def result_created_email(instance: Result, created: bool = False, *_, **__):
    if created:
        # Only send emails on created, as EVERY result for this challenge is
        # updated when the results are recalculated
        send_new_result_email(instance)


# TODO: do we really want to generate an API token for all users? Only admins?
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(
    instance: settings.AUTH_USER_MODEL = None, created: bool = False, *_, **__
):
    # Ignore the anonymous user which is created by userena on initial
    # migration
    if created and instance.username != settings.ANONYMOUS_USER_NAME:
        Token.objects.create(user=instance)
