from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from evaluation.models import Submission, Job, Method
from evaluation.tasks import evaluate_submission


@receiver(post_save, sender=Submission)
def create_evaluation_job(sender: Submission, instance: Submission = None,
                          created: bool = False, **kwargs):
    if created:
        method = Method.objects.filter(
            challenge__pk=instance.challenge.pk).order_by('-created').first()

        if method is None:
            # TODO: Email here, do not raise
            # raise NoMethodForChallengeError
            pass
        else:
            Job.objects.create(submission=instance, method=method)


@receiver(post_save, sender=Job)
def execute_job(sender: Job, instance: Job = None, created: bool = False,
                **kwargs):
    if created:
        # TODO: Create Timeout tests
        evaluate_submission.apply_async(task_id=str(instance.pk),
                                        kwargs={'job_pk': instance.pk})


# TODO: generate an auth token for all users
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender: settings.AUTH_USER_MODEL,
                      instance: settings.AUTH_USER_MODEL = None,
                      created: bool = False, **kwargs):
    # Ignore the anonymous user which is created by userena on initial
    # migration
    if created and instance.username != settings.ANONYMOUS_USER_NAME:
        Token.objects.create(user=instance)
