from django.db import models
from grandchallenge.core.models import UUIDModel
from grandchallenge.retina_images.models import RetinaImage


class Archive(UUIDModel):
    """
    Model for archive. Contains a collection of images
    """

    name = models.CharField(max_length=255, default="Unnamed Archive")

    images = models.ManyToManyField(RetinaImage)

    def __str__(self):
        return "<{} {}>".format(self.__class__.__name__, self.name)
