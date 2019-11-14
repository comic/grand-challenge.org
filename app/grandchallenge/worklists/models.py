from django.conf import settings
from django.db import models
from django.db.models import CharField

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel


class Worklist(UUIDModel):
    """Represents a collection of images for a user."""

    title = CharField(max_length=255, blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    images = models.ManyToManyField(
        to=Image, related_name="worklist", blank=True
    )

    def __str__(self):
        return "{} ({})".format(self.title, str(self.id))
