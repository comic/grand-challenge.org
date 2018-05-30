# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.validators import ExtensionValidator


def case_file_path(instance, filename):
    return f"cases/{instance.pk}/{filename}"


class Case(UUIDModel):
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    file = models.FileField(
        upload_to=case_file_path,
        validators=[ExtensionValidator(allowed_extensions=('.mha',))],
        help_text=(
            'Select the .mha file that you want to use.'
        ),
    )

    def get_absolute_url(self):
        return reverse("cases:detail", kwargs={"pk": self.pk})
