# -*- coding: utf-8 -*-
from django.contrib.postgres.fields import JSONField
from django.db import models

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.urlresolvers import reverse


def case_file_path(instance, filename):
    return f"cases/{instance.case.pk}/{filename}"


class UPLOAD_SESSION_STATE:
    created = "created"
    queued = "queued"
    running = "running"
    stopped = "stopped"


class RawImageUploadSession(UUIDModel):
    """
    A session keeps track of uploaded files and forms the basis of a processing
    task that tries to make sense of the uploaded files to form normalized
    images that can be fed to processing tasks.
    """
    session_state = models.CharField(
        max_length=16,
        default=UPLOAD_SESSION_STATE.created,
    )

    processing_task = models.UUIDField(
        null=True,
        default=None,
    )

    error_message = models.CharField(
        max_length=256,
        blank=False,
        null=True,
        default=None,
    )

    def get_absolute_url(self):
        return reverse(
            "cases:raw-files-session-detail",
            kwargs={
                "pk": self.pk,
            })


class RawImageFile(UUIDModel):
    """
    A raw image file is a file that has been uploaded by a user but was not
    preprocessed to create a standardized image representation.
    """
    upload_session = models.ForeignKey(
        RawImageUploadSession,
        blank=False,
        on_delete=models.CASCADE,
    )

    # Copy in case staged_file_id is set to None
    filename = models.CharField(
        max_length=128,
        blank=False,
    )

    staged_file_id = models.UUIDField(
        blank=True,
        null=True)

    error = models.CharField(
        max_length=256,
        blank=False,
        null=True,
        default=None
    )


def image_file_path(instance, filename):
    return f"images/{instance.image.pk}/{filename}"


class Image(UUIDModel):
    COLOR_SPACE_GRAY = "GRAY"
    COLOR_SPACE_RGB = "RGB"
    COLOR_SPACE_RGBA = "RGBA"

    COLOR_SPACES = (
        (COLOR_SPACE_GRAY, "GRAY"),
        (COLOR_SPACE_RGB, "RGB"),
        (COLOR_SPACE_RGBA, "RGBA"),
    )

    COLOR_SPACE_COMPONENTS = {
        COLOR_SPACE_GRAY: 1,
        COLOR_SPACE_RGB: 3,
        COLOR_SPACE_RGBA: 4,
    }

    name = models.CharField(max_length=128)
    origin = models.ForeignKey(
        to=RawImageUploadSession,
        null=True,
        on_delete=models.SET_NULL,
    )

    width = models.IntegerField(
        blank=False,
    )
    height = models.IntegerField(
        blank=False,
    )
    depth = models.IntegerField(
        null=True,
    )
    color_space = models.CharField(
        max_length=4,
        blank=False,
        choices=COLOR_SPACES,
    )

    @property
    def shape_without_color(self):
        result = []
        if self.depth is not None:
            result.append(self.depth)
        result.append(self.height)
        result.append(self.width)
        return result

    @property
    def shape(self):
        result = self.shape_without_color
        color_components = self.COLOR_SPACE_COMPONENTS[self.color_space]
        if color_components > 1:
            result.append(color_components)
        return result


class ImageFile(UUIDModel):
    image = models.ForeignKey(
        to=Image,
        null=True,
        on_delete=models.SET_NULL,
    )
    file = models.FileField(
        upload_to=image_file_path,
        blank=False,
    )


class Annotation(UUIDModel):
    """
    An object that represents an annotation of an image. This can be another
    image, for instance, a segmentation, or some metadata such as a
    classification, eg. {"cancer": False}.
    """
    of = models.ForeignKey(
        Image, related_name="annotations", on_delete=models.CASCADE,
    )
    image = models.ForeignKey(
        Image, null=True, on_delete=models.CASCADE,
    )
    metadata = JSONField()
