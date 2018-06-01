import uuid

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

class CeleryJobModel(models.Model):
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
        (
            FAILURE,
            'The task raised an exception, or has exceeded the retry limit',
        ),
        (SUCCESS, 'The task executed successfully'),
        (CANCELLED, 'The task was cancelled'),
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING
    )
    status_history = JSONField(default=dict)
    output = models.TextField()

    def update_status(self, *, status: STATUS_CHOICES, output: str = None):
        self.status = status

        if output:
            self.output = output

        self.save()

    class Meta:
        abstract = True
