from django.contrib.postgres.fields import CICharField
from django.db import models


class BodyRegion(models.Model):
    """Store the anatomy options, eg, Head, Neck, Thorax, etc."""

    region = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("region",)

    def __str__(self):
        return self.region
