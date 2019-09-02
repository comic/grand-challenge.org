from django.db import models
from grandchallenge.core.models import UUIDModel
from grandchallenge.cases.models import Image
from grandchallenge.patients.models import Patient


class Archive(UUIDModel):
    """
    Model for archive. Contains a collection of images
    """

    name = models.CharField(max_length=255, default="Unnamed Archive")

    images = models.ManyToManyField(Image)

    def __str__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    def delete(self, *args, **kwargs):
        # Remove all related patients and other models via cascading
        Patient.objects.filter(study__image__archive__id=self.id).delete(
            *args, **kwargs
        )
        super().delete(*args, **kwargs)
