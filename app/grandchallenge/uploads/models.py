import os

from django.db import models
from django.db.models import SET_NULL
from django.utils.datetime_safe import strftime
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django_summernote.models import AbstractAttachment

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import public_s3_storage


def public_media_filepath(instance, filename):
    if instance.challenge:
        subfolder = os.path.join("challenge", str(instance.challenge.pk))
    else:
        subfolder = "none"

    return os.path.join(
        "f", subfolder, str(instance.pk), get_valid_filename(filename)
    )


class PublicMedia(UUIDModel):
    file = models.FileField(
        upload_to=public_media_filepath, storage=public_s3_storage
    )
    challenge = models.ForeignKey(
        Challenge, null=True, blank=True, default=None, on_delete=SET_NULL
    )


def summernote_upload_filepath(instance, filename):
    return os.path.join(
        strftime(now(), "i/%Y/%m/%d"), get_valid_filename(filename),
    )


class SummernoteAttachment(AbstractAttachment):
    """Workaround for custom upload locations from summernote."""

    file = models.FileField(
        upload_to=summernote_upload_filepath, storage=public_s3_storage
    )
