from django.contrib.postgres.fields import ArrayField
from django.db import models

from grandchallenge.cases.models import Image
from grandchallenge.core.models import UUIDModel


class OctObsRegistration(UUIDModel):
    """Model for registration of Topcon OCT to OBS files."""

    obs_image = models.ForeignKey(
        Image, related_name="obs_image", on_delete=models.CASCADE
    )
    oct_image = models.ForeignKey(
        Image, related_name="oct_image", on_delete=models.CASCADE
    )

    # Registration values in this form: [[top_left_x, top_left_y],[bottom_right_x, bottom_right_y]]
    registration_values = ArrayField(
        ArrayField(models.FloatField(), size=2), size=2
    )

    class Meta(UUIDModel.Meta):
        unique_together = ("obs_image", "oct_image")
