# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.forms import UUIDField
from django.utils import timezone

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.evaluation.validators import ExtensionValidator
from grandchallenge.jqfileupload.models import StagedFile


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


def image_file_path(instance, filename):
    return f"images/{instance.case.pk}/{filename}"


class Image(UUIDModel):
    name = models.CharField(max_length=128)
    image_handle = models.TextField()


class RawImageUploadSession(UUIDModel):
    """
    A session keeps track of uploaded files and forms the basis of a processing
    task that tries to make sense of the uploaded files to form normalized
    images that can be fed to processing tasks.
    """
    session_state = models.CharField(max_length=16)

    created_on = models.DateTimeField(
        blank=False,
        default=timezone.now,
    )

    def get_absolute_url(self):
        return reverse("cases:raw-files-session-detail")


class RawImageFile(UUIDModel):
    """
    A raw image file is a file that has been uploaded by a user but was not
    preprocessed to create a standardized image representation.
    """
    upload_session = models.ForeignKey(
        RawImageUploadSession,
        null=True,
        on_delete=models.SET_NULL,
    )

    staged_file_id = models.UUIDField(blank=False)
