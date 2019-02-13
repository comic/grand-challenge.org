from django.db import models
from grandchallenge.core.models import UUIDModel


class Patient(UUIDModel):
    """
    Top level datastructure, contains many studies that contain many images
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return "<{} {}>".format(self.__class__.__name__, self.name)

    class Meta(UUIDModel.Meta):
        unique_together = ("name",)
