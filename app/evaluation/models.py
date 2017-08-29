import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from social_django.fields import JSONField


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
    This model stores individual results for a challenges
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


class Method(UUIDModel):
    """
    This model stores the methods for performing an evaluation
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
    """
    Determine where the uploaded submission should be stored.
    Will be created relative to MEDIA_ROOT.

    :param instance: The instance of the model
    :param filename: The given filename
    :return: The path that the file will be uploaded to
    """
    return 'evaluation/{0}/submission/{1}/{2}/{3}' \
        .format(instance.challenge.id,
                instance.user.id,
                instance.created.strftime('%Y%m%d%H%M%S'),
                filename)


class Submission(UUIDModel):
    """
    This model stores files for evaluation
    """
    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    file = models.FileField(upload_to=challenge_submission_path)


class Job(UUIDModel):
    """
    This model stores information about a job for a given upload
    """
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (INACTIVE, 'Inactive'),
        (QUEUED, 'Queued'),
        (RUNNING, 'Running'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
        (CANCELLED, 'Cancelled')
    )

    submission = models.ForeignKey('Submission',
                                   null=True,
                                   on_delete=models.SET_NULL)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=INACTIVE)

    status_history = JSONField(default=dict)

    output = models.TextField()
