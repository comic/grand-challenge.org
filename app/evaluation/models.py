import uuid

from django.contrib.auth.models import User
from django.db import models
from social_django.fields import JSONField
from evaluation.validators import MimeTypeValidator


class UUIDModel(models.Model):
    """
    Abstract class that consists of a UUID primary key, created and modified
    times
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Result(UUIDModel):
    """
    Stores individual results for a challenges
    """
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    metrics = JSONField(default=dict)

    public = models.BooleanField(default=True)


def result_screenshot_path(instance, filename):
    return 'evaluation/{0}/screenshots/{1}/{2}' \
        .format(instance.challenge.id,
                instance.result.id,
                filename)


class ResultScreenshot(UUIDModel):
    """
    Stores a screenshot that is generated during an evaluation
    """
    result = models.ForeignKey('Result',
                               on_delete=models.CASCADE)

    image = models.ImageField(upload_to=result_screenshot_path)


class Method(UUIDModel):
    """
    Stores the methods for performing an evaluation
    """
    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    image_repository = models.CharField(max_length=128)

    image_tag = models.CharField(max_length=64)

    image_sha256 = models.CharField(max_length=64)

    version = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("challenge", "version"),)


def challenge_submission_path(instance, filename):
    return 'evaluation/{0}/submission/{1}/{2}/{3}' \
        .format(instance.challenge.id,
                instance.user.id,
                instance.created.strftime('%Y%m%d%H%M%S'),
                filename)


class Submission(UUIDModel):
    """
    Stores files for evaluation
    """
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    file = models.FileField(upload_to=challenge_submission_path,
                            validators=[MimeTypeValidator(
                                allowed_mimetypes=('application/pdf',))])

    description = models.FileField(upload_to=challenge_submission_path,
                                   validators=[MimeTypeValidator(
                                       allowed_mimetypes=(
                                       'application/pdf',))])


class Job(UUIDModel):
    """
    Stores information about a job for a given upload
    """

    # The job statuses come directly from celery.result.AsyncResult.status:
    # http://docs.celeryproject.org/en/latest/reference/celery.result.html
    PENDING = 0
    STARTED = 1
    RETRY = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, 'The task is waiting for execution'),
        (STARTED, 'The task has been started'),
        (RETRY, 'The task is to be retried, possibly because of failure'),
        (FAILURE,
         'The task raised an exception, or has exceeded the retry limit'),
        (SUCCESS, 'The task executed successfully'),
        (CANCELLED, 'The task was cancelled')
    )

    submission = models.ForeignKey('Submission',
                                   null=True,
                                   on_delete=models.SET_NULL)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=PENDING)

    status_history = JSONField(default=dict)

    output = models.TextField()
