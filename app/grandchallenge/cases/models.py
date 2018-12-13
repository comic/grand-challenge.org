from typing import List

from django.conf import settings
from django.db import models

from grandchallenge.challenges.models import Challenge
from grandchallenge.core.models import UUIDModel
from grandchallenge.subdomains.utils import reverse


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

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    session_state = models.CharField(
        max_length=16, default=UPLOAD_SESSION_STATE.created
    )

    processing_task = models.UUIDField(null=True, default=None)

    error_message = models.CharField(
        max_length=256, blank=False, null=True, default=None
    )

    imageset = models.ForeignKey(
        to="datasets.ImageSet",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    annotationset = models.ForeignKey(
        to="datasets.AnnotationSet",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    algorithm = models.ForeignKey(
        to="algorithms.Algorithm",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    algorithm_result = models.OneToOneField(
        to="algorithms.Result",
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            f"Upload Session <{str(self.pk).split('-')[0]}>, "
            f"({self.session_state})"
        )

    def save(self, *args, skip_processing=False, **kwargs):

        created = self._state.adding

        super().save(*args, **kwargs)

        if created and not skip_processing:
            self.process_images()

    def process_images(self):
        # Local import to avoid circular dependency
        from grandchallenge.cases.tasks import build_images

        try:
            RawImageUploadSession.objects.filter(pk=self.pk).update(
                session_state=UPLOAD_SESSION_STATE.queued,
                processing_task=self.pk,
            )

            build_images.apply_async(task_id=str(self.pk), args=(self.pk,))

        except Exception as e:
            RawImageUploadSession.objects.filter(pk=self.pk).update(
                session_state=UPLOAD_SESSION_STATE.stopped,
                error_message=f"Could not start job: {e}",
            )
            raise e

    def get_absolute_url(self):
        return reverse(
            "cases:raw-files-session-detail", kwargs={"pk": self.pk}
        )


class RawImageFile(UUIDModel):
    """
    A raw image file is a file that has been uploaded by a user but was not
    preprocessed to create a standardized image representation.
    """

    upload_session = models.ForeignKey(
        RawImageUploadSession, blank=False, on_delete=models.CASCADE
    )

    # Copy in case staged_file_id is set to None
    filename = models.CharField(max_length=128, blank=False)

    staged_file_id = models.UUIDField(blank=True, null=True)

    error = models.CharField(
        max_length=256, blank=False, null=True, default=None
    )


def image_file_path(instance, filename):
    return f"images/{instance.image.pk}/{filename}"


def case_file_path(instance, filename):
    # legacy method, but used in a migration so cannot delete.
    return image_file_path(instance, filename)


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
        to=RawImageUploadSession, null=True, on_delete=models.SET_NULL
    )

    width = models.IntegerField(blank=False)
    height = models.IntegerField(blank=False)
    depth = models.IntegerField(null=True)
    color_space = models.CharField(
        max_length=4, blank=False, choices=COLOR_SPACES
    )

    def __str__(self):
        return f"Image {self.name} {self.shape_without_color}"

    @property
    def shape_without_color(self) -> List[int]:
        result = []
        if self.depth is not None:
            result.append(self.depth)
        result.append(self.height)
        result.append(self.width)
        return result

    @property
    def shape(self) -> List[int]:
        result = self.shape_without_color
        color_components = self.COLOR_SPACE_COMPONENTS[self.color_space]
        if color_components > 1:
            result.append(color_components)
        return result

    @property
    def cirrus_link(self) -> str:
        return f"{settings.CIRRUS_APPLICATION}&{settings.CIRRUS_BASE_IMAGE_QUERY_PARAM}={self.pk}"

    class Meta:
        ordering = ("name",)


class ImageFile(UUIDModel):
    image = models.ForeignKey(
        to=Image, null=True, on_delete=models.SET_NULL, related_name="files"
    )
    file = models.FileField(upload_to=image_file_path, blank=False)
