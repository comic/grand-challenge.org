from django.contrib.auth.models import User
from django.db import models
from django.db.models import CharField
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image


class Worklist(UUIDModel):
    """
    Represents a collection of images for a user.
    """

    title = CharField(max_length=255)
    user = models.ForeignKey(
        User, blank=True, null=True, on_delete=models.CASCADE
    )
    images = models.ManyToManyField(
        to=Image, related_name="worklist", blank=True
    )

    def __str__(self):
        return "{} ({})".format(self.title, str(self.id))
