from django.db import models
from django_deprecate_fields import deprecate_field

from grandchallenge.core.models import UUIDModel
from grandchallenge.patients.models import Patient


class Study(UUIDModel):
    """Middle level datastructure. Child of patient, contains many images."""

    patient = deprecate_field(
        models.ForeignKey(Patient, on_delete=models.CASCADE)
    )

    datetime = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The date and time at which this study took place",
    )
    name = models.CharField(max_length=255)

    def __str__(self):
        return "{} <{} {}>".format(
            self.patient, self.__class__.__name__, self.name
        )
