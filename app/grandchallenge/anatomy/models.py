from django.contrib.postgres.fields import CICharField
from django.db import models
from django.utils.html import format_html


class BodyRegion(models.Model):
    """Store the anatomy options, eg, Head, Neck, Thorax, etc."""

    region = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("region",)

    def __str__(self):
        return self.region


class BodyStructure(models.Model):
    """Store the organ name and what region it belongs to."""

    structure = CICharField(max_length=16, blank=False, unique=True)
    region = models.ForeignKey(
        to=BodyRegion, on_delete=models.CASCADE, blank=False
    )

    class Meta:
        ordering = ("region", "structure")

    def __str__(self):
        return f"{self.structure} ({self.region})"

    @property
    def badge(self):
        return format_html(
            (
                '<span class="badge badge-dark above-stretched-link" '
                'title="Uses {0} data"><i class="fas fa-child fa-fw">'
                "</i> {0}</span>"
            ),
            self.structure,
        )
