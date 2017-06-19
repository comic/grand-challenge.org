import uuid

from django.contrib.auth.models import User
from django.db import models
from social_django.fields import JSONField


class Result(models.Model):
    """
    This model stores individual results for a given challenge
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    job = models.ForeignKey('Job',
                            null=True,
                            on_delete=models.SET_NULL)

    user = models.ForeignKey(User,
                             null=True,
                             on_delete=models.SET_NULL)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    method = models.ForeignKey('Method',
                               null=True,
                               on_delete=models.SET_NULL)

    metrics = JSONField(default=dict)


class Method(models.Model):
    """
    This model stores the methods for performing an evaluation
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    challenge = models.ForeignKey('comicmodels.ComicSite',
                                  on_delete=models.CASCADE)

    source = models.ForeignKey('comicmodels.UploadModel',
                               null=True,
                               on_delete=models.SET_NULL)

    version = models.PositiveIntegerField(default=0)


class Job(models.Model):
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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    submitted_file = models.ForeignKey('comicmodels.UploadModel',
                                       null=True,
                                       on_delete=models.SET_NULL)

    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
                                              default=INACTIVE)
    status_history = JSONField(default=dict)
    output = models.TextField()
