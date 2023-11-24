from django.db import models
from django.utils.html import format_html


class Incentive(models.Model):
    """Store the incentive options, eg, Monetary, Publication, Speaking Engagement."""

    incentive = models.CharField(max_length=24, blank=False, unique=True)

    class Meta:
        ordering = ("incentive",)

    def __str__(self):
        return self.incentive

    @property
    def badge(self):
        return format_html(
            (
                '<span class="badge badge-secondary above-stretched-link" '
                'title="Uses {0} data"><i class="fas fa-trophy fa-fw">'
                "</i> {0}</span>"
            ),
            self.incentive,
        )
