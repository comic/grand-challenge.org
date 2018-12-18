from django.db import models
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image


class Archive(UUIDModel):
    """
    Model for archive. Contains a collection of images
    """

    name = models.CharField(max_length=255, default="Unnamed Archive")

    images = models.ManyToManyField(Image)

    def __str__(self):
        return "<{} {}>".format(self.__class__.__name__, self.name)
