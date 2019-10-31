from typing import Union

from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.datasets.models import ImageSet
from grandchallenge.evaluation.emails import send_new_result_email
from grandchallenge.evaluation.models import (
    Config,
    Job,
    Method,
    Result,
    Submission,
)
from grandchallenge.evaluation.tasks import calculate_ranks
from grandchallenge.submission_conversion.models import (
    SubmissionToAnnotationSetJob,
)


@receiver(post_save, sender=Submission)
@disable_for_loaddata
def create_evaluation_job(
    instance: Submission = None, created: bool = False, *_, **__
):
    if created:
        method = (
            Method.objects.filter(challenge=instance.challenge)
            .order_by("-created")
            .first()
        )

        if method is None:
            # TODO: Email here, do not raise
            # raise NoMethodForChallengeError
            pass
        else:
            Job.objects.create(submission=instance, method=method)

        # Convert this submission to an annotation set
        base = ImageSet.objects.get(
            challenge=instance.challenge, phase=ImageSet.TESTING
        )
        SubmissionToAnnotationSetJob.objects.create(
            base=base, submission=instance
        )


@receiver(post_save, sender=Config)
@receiver(post_save, sender=Result)
@disable_for_loaddata
def recalculate_ranks(instance: Union[Result, Config] = None, *_, **__):
    """Recalculates the ranking on a new result"""
    try:
        challenge_pk = instance.challenge.pk
    except AttributeError:
        # For a Result
        challenge_pk = instance.job.submission.challenge.pk

    calculate_ranks.apply_async(kwargs={"challenge_pk": challenge_pk})


@receiver(post_save, sender=Result)
@disable_for_loaddata
def result_created_email(instance: Result, created: bool = False, *_, **__):
    if created:
        # Only send emails on created, as EVERY result for this challenge is
        # updated when the results are recalculated
        send_new_result_email(instance)
