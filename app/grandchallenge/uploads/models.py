import os

from django.conf import settings
from django.db import models
from django.utils.datetime_safe import strftime
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django_summernote.models import AbstractAttachment

from grandchallenge.challenges.models import ComicSiteModel
from grandchallenge.core.storage import public_s3_storage


def give_file_upload_destination_path(uploadmodel, filename):
    """
    Where should this file go relative to MEDIA_ROOT?

    Determines location based on permission level of the uploaded model.
    """
    # uploadmodel can be either a Challenge, meaning a
    # header image or something belonging to a Challenge is being uploaded, or
    # a Page, meaning it is some inheriting class
    # TODO: This is confused code. Have a single way of handling uploads,
    # lika a small js browser with upload capability.
    if hasattr(uploadmodel, "short_name"):
        challenge = uploadmodel
        # Any image uploaded as part of a comcisite is public. These images
        # are only headers and other public things
        permission_lvl = ComicSiteModel.ALL
    else:
        challenge = uploadmodel.challenge
        permission_lvl = uploadmodel.permission_lvl

    # If permission is ALL, upload this file to the public_html folder
    if permission_lvl == ComicSiteModel.ALL:
        path = os.path.join(
            challenge.public_upload_dir_rel(), get_valid_filename(filename)
        )
    else:
        path = os.path.join(
            challenge.upload_dir_rel(), get_valid_filename(filename)
        )

    # replace remove double slashes because this can mess up django's url
    # system
    path = path.replace("\\", "/")
    return path


class UploadModel(ComicSiteModel):
    file = models.FileField(
        max_length=255, upload_to=give_file_upload_destination_path
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        help_text="which user uploaded this?",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta(ComicSiteModel.Meta):
        verbose_name = "uploaded file"
        verbose_name_plural = "uploaded files"


def summernote_upload_filepath(instance, filename):
    return os.path.join(
        strftime(now(), "i/%Y/%m/%d"), get_valid_filename(filename),
    )


class SummernoteAttachment(AbstractAttachment):
    """Workaround for custom upload locations from summernote."""

    file = models.FileField(
        upload_to=summernote_upload_filepath, storage=public_s3_storage
    )
