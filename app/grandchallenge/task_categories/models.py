from django.contrib.postgres.fields import CICharField
from django.db import models
from django.utils.html import format_html


class TaskType(models.Model):
    """Stores the task type options, eg, Segmentation, Regression, etc."""

    type = CICharField(max_length=16, blank=False, unique=True)

    class Meta:
        ordering = ("type",)

    def __str__(self):
        return self.type

    @property
    def badge(self):
        return format_html(
            (
                '<span class="badge badge-light above-stretched-link" '
                'title="{0} challenge"><i class="fas fa-tasks fa-fw">'
                "</i> {0}</span>"
            ),
            self.type,
        )
