from django.contrib.postgres.fields import CICharField
from django.db import models
from django.utils.html import format_html


class ImagingModality(models.Model):
    """Store the modality options, eg, MR, CT, PET, XR."""

    modality = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("modality",)

    def __str__(self):
        return self.modality

    @property
    def badge(self):
        return format_html(
            (
                '<span class="badge badge-secondary above-stretched-link" '
                'title="Uses {0} data"><i class="fas fa-microscope fa-fw">'
                "</i> {0}</span>"
            ),
            self.modality,
        )
