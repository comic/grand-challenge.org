# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.validators import ExtensionValidator


def case_file_path(instance, filename):
    return f"cases/{instance.case.pk}/{filename}"


class Case(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )

    def get_absolute_url(self):
        return reverse("cases:detail", kwargs={"pk": self.pk})


class CaseFile(UUIDModel):
    case = models.ForeignKey(to=Case, on_delete=models.CASCADE)

    file = models.FileField(
        upload_to=case_file_path,
        validators=[
            ExtensionValidator(
                allowed_extensions=('.mhd', '.raw', '.zraw',)
            )
        ],
        help_text=(
            'Select the file for this case.'
        ),
    )
