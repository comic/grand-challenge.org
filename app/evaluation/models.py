import uuid

from django.contrib.auth.models import User
from django.db import models
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


def challenge_method_path(instance, filename):
    """
    Determine where the method source will be uploaded to, relative to
    MEDIA_ROOT
    :param instance: The instance of the model for the upload
    :param filename: The filename as given by the user
    :return: The upload path
    """
    return 'evaluation/challenge_{0}/method/version_{1}/{2}' \
        .format(instance.challenge.id, instance.version, filename)


class Method(UUIDModel):
    """
    This model stores the methods for performing an evaluation
    """
    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    source = models.FileField(upload_to=challenge_method_path)

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
    return 'evaluation/challenge_{0}/submission/user_{1}/{2}/{3}' \
        .format(instance.challenge.id, instance.user.id, instance.created,
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

    class Meta:
        # Ensure that there is only 1 submission at a time for each challenge
        unique_together = (("user", "challenge", "created"),)


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
