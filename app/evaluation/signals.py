from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from evaluation.models import Submission, Job
from evaluation.tasks import evaluate_submission


@receiver(post_save, sender=Submission)
def create_evaluation_job(sender: Submission, instance: Submission = None,
                          created: bool = False, **kwargs):
    if created:
        evaluation_job = Job.objects.create(submission_id=instance.id)
        evaluate_submission.apply_async(task_id=str(evaluation_job.id),
                                        kwargs={'job_id': evaluation_job.id})


# TODO: generate an auth token for all users
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender: User, instance: User = None,
                      created: bool = False, **kwargs):
    # Ignore the anonymous user which is created by userena on initial
    # migration
    if created and instance.pk != settings.ANONYMOUS_USER_ID:
        Token.objects.create(user=instance)
