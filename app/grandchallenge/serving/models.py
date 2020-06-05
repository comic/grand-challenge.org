from django.conf import settings
from django.db import models

from grandchallenge.cases.models import Image
from grandchallenge.evaluation.models import Submission


class Download(models.Model):
    """Tracks who downloaded image or submission objects."""

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    # Allow null creators to anonymous users
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )

    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)
    submission = models.ForeignKey(
        Submission, null=True, on_delete=models.CASCADE
    )

    count = models.BigIntegerField(default=1)

    class Meta:
        unique_together = ("creator", "image", "submission")
