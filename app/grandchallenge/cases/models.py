import gzip
import hashlib
import json
import logging
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import NamedTuple
from urllib.parse import urlparse

import boto3
from actstream.actions import follow
from billiard.exceptions import SoftTimeLimitExceeded
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError
from celery import signature
from cffi.model import NamedPointerType
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, SuspiciousFileOperation
from django.db import models
from django.db.models.signals import post_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.template.defaultfilters import pluralize
from django.utils._os import safe_join
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from grand_challenge_dicom_de_identifier.deidentifier import DicomDeidentifier
from guardian.shortcuts import assign_perm, get_groups_with_perms, remove_perm
from panimg.image_builders.metaio_utils import load_sitk_image
from panimg.models import (
    MAXIMUM_SEGMENTS_LENGTH,
    ColorSpace,
    ImageType,
    PatientSex,
)
from pydantic import ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from pydantic.dataclasses import dataclass
from storages.utils import clean_name

from grandchallenge.core.error_handlers import (
    RawImageUploadSessionErrorHandler,
)
from grandchallenge.core.guardian import (
    GroupObjectPermissionBase,
    UserObjectPermissionBase,
)
from grandchallenge.core.models import FieldChangeMixin, UUIDModel
from grandchallenge.core.storage import protected_s3_storage
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.validators import JSONValidator
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload

logger = logging.getLogger(__name__)


SEGMENTS_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "array",
    "title": "The Segments Schema",
    "items": {
        "$id": "#/items",
        "type": "integer",
        "maxItems": MAXIMUM_SEGMENTS_LENGTH,
    },
    "uniqueItems": True,
}

IMPORT_JOB_FAILURE_NDJSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "inputFile": {"type": "string"},
            "exception": {
                "type": "object",
                "properties": {
                    "exceptionType": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["exceptionType", "message"],
            },
        },
        "required": ["inputFile", "exception"],
    },
}


class RawImageUploadSession(UUIDModel):
    """
    A session keeps track of uploaded files and forms the basis of a processing
    task that tries to make sense of the uploaded files to form normalized
    images that can be fed to processing tasks.
    """

    PENDING = 0
    STARTED = 1
    REQUEUED = 2
    FAILURE = 3
    SUCCESS = 4
    CANCELLED = 5

    STATUS_CHOICES = (
        (PENDING, "Queued"),
        (STARTED, "Started"),
        (REQUEUED, "Re-Queued"),
        (FAILURE, "Failed"),
        (SUCCESS, "Succeeded"),
        (CANCELLED, "Cancelled"),
    )

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )

    user_uploads = models.ManyToManyField(
        UserUpload, blank=True, related_name="image_upload_sessions"
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )

    import_result = models.JSONField(
        blank=True, null=True, default=None, editable=False
    )

    error_message = models.TextField(blank=True)

    def __str__(self):
        return (
            f"Upload Session <{str(self.pk).split('-')[0]}>, "
            f"({self.get_status_display()}) "
            f"{self.error_message}"
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            if self.creator:
                # The creator can view this upload session
                assign_perm(
                    f"view_{self._meta.model_name}", self.creator, self
                )
                assign_perm(
                    f"change_{self._meta.model_name}", self.creator, self
                )
                follow(
                    user=self.creator,
                    obj=self,
                    send_action=False,
                    actor_only=False,
                )

    @property
    def default_error_message(self):
        n_errors = self.import_result and len(
            self.import_result["file_errors"]
        )
        if n_errors:
            return (
                f"{n_errors} file{pluralize(n_errors)} could not be imported"
            )
        else:
            return ""

    def get_error_handler(self, *, linked_object=None):
        return RawImageUploadSessionErrorHandler(
            upload_session=self,
            linked_object=linked_object,
        )

    def update_status(
        self,
        *,
        status,
        error_message=None,
        detailed_error_message=None,
    ):
        self.status = status

        if detailed_error_message:
            notification_description = oxford_comma(
                [
                    f"Image validation for socket {key} failed with error: {val}."
                    for key, val in detailed_error_message.items()
                ]
            )
        elif error_message:
            notification_description = error_message
        else:
            notification_description = self.default_error_message

        self.error_message = notification_description
        self.save()

        if notification_description and self.creator:
            Notification.send(
                kind=NotificationTypeChoices.IMAGE_IMPORT_STATUS,
                description=notification_description,
                action_object=self,
            )

    def process_images(
        self,
        *,
        linked_app_label=None,
        linked_model_name=None,
        linked_object_pk=None,
        linked_interface_slug=None,
        linked_task=None,
    ):
        """
        Starts the Celery task to import this RawImageUploadSession.

        Parameters
        ----------
        linked_task
            A celery task that will be executed on success of the build_images
            task, with 1 keyword argument: upload_session_pk=self.pk
        """

        # Local import to avoid circular dependency
        from grandchallenge.cases.tasks import build_images

        if self.status != self.PENDING:
            raise RuntimeError("Job is not in PENDING state")

        RawImageUploadSession.objects.filter(pk=self.pk).update(
            status=RawImageUploadSession.REQUEUED
        )

        # The linked task is updated here so we can define it on forms
        # before the upload session instance exists.
        if linked_task is not None:
            linked_task.kwargs.update({"upload_session_pk": self.pk})

        on_commit(
            build_images.signature(
                kwargs={
                    "upload_session_pk": self.pk,
                    "linked_app_label": linked_app_label,
                    "linked_model_name": linked_model_name,
                    "linked_object_pk": linked_object_pk,
                    "linked_interface_slug": linked_interface_slug,
                    "linked_task": linked_task,
                }
            ).apply_async
        )

    def get_absolute_url(self):
        return reverse(
            "cases:raw-image-upload-session-detail", kwargs={"pk": self.pk}
        )

    @property
    def api_url(self) -> str:
        return reverse("api:upload-session-detail", kwargs={"pk": self.pk})


class RawImageUploadSessionUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset(
        {"change_rawimageuploadsession", "view_rawimageuploadsession"}
    )

    content_object = models.ForeignKey(
        RawImageUploadSession, on_delete=models.CASCADE
    )


class RawImageUploadSessionGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset()

    content_object = models.ForeignKey(
        RawImageUploadSession, on_delete=models.CASCADE
    )


def image_file_path(instance, filename):
    return (
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/"
        f"{str(instance.image.pk)[0:2]}/"
        f"{str(instance.image.pk)[2:4]}/"
        f"{instance.image.pk}/"
        f"{instance.pk}/"
        f"{get_valid_filename(filename)}"
    )

class DICOMInstanceRequest(NamedTuple):
    sop_instance_uid: str
    unsigned_request: AWSRequest


class DICOMImageSet(UUIDModel):
    image_set_id = models.CharField(
        max_length=32,
        unique=True,
        help_text="The ID of the image set in AWS Health Imaging",
        editable=False,
    )
    image_frame_metadata = models.JSONField(
        editable=False,
        help_text="The metadata of the image frames in AWS Health Imaging",
        validators=[
            JSONValidator(
                schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "image_frame_id",
                            "frame_size_in_bytes",
                            "study_instance_uid",
                            "series_instance_uid",
                            "sop_instance_uid",
                            "stored_transfer_syntax_uid",
                        ],
                        "additionalProperties": False,
                        "properties": {
                            "image_frame_id": {
                                "type": "string",
                                "pattern": "^[0-9a-f]{32}$",
                                "minLength": 32,
                                "maxLength": 32,
                            },
                            "frame_size_in_bytes": {
                                "type": "integer",
                                "min_value": 0,
                            },
                            "study_instance_uid": {
                                "type": "string",
                                "pattern": "^[0-9.]*$",
                                "minLength": 60,
                                "maxLength": 64,
                            },
                            "series_instance_uid": {
                                "type": "string",
                                "pattern": "^[0-9.]*$",
                                "minLength": 60,
                                "maxLength": 64,
                            },
                            "sop_instance_uid": {
                                "type": "string",
                                "pattern": "^[0-9.]*$",
                                "minLength": 60,
                                "maxLength": 64,
                            },
                            "stored_transfer_syntax_uid": {
                                "type": "string",
                                "pattern": "^1.2.840.10008.1.2[0-9.]*$",
                                "minLength": 19,
                                "maxLength": 25,
                            },
                        },
                    },
                    "minItems": 1,
                }
            )
        ],
    )
    dicom_image_set_upload = models.OneToOneField(
        to="DICOMImageSetUpload",
        editable=False,
        on_delete=models.PROTECT,
        related_name="dicom_image_set",
    )

    @property
    def instance_requests(self):
        for image_frame in self.image_frame_metadata:
            study_instance_uid = image_frame["study_instance_uid"]
            series_instance_uid = image_frame["series_instance_uid"]
            sop_instance_uid = image_frame["sop_instance_uid"]
            stored_transfer_syntax_uid = image_frame[
                "stored_transfer_syntax_uid"
            ]

            # See https://docs.aws.amazon.com/healthimaging/latest/devguide/dicomweb-retrieve-instance.html
            dicom_file_url = (
                f"https://dicom-medical-imaging.{settings.AWS_DEFAULT_REGION}.amazonaws.com"
                f"/datastore/{settings.AWS_HEALTH_IMAGING_DATASTORE_ID}"
                f"/studies/{study_instance_uid}"
                f"/series/{series_instance_uid}"
                f"/instances/{sop_instance_uid}"
                f"?imageSetId={self.image_set_id}"
            )

            yield DICOMInstanceRequest(
                sop_instance_uid=sop_instance_uid,
                unsigned_request=AWSRequest(
                    method="GET",
                    url=dicom_file_url,
                    headers={
                        "Accept": f"application/dicom; transfer-syntax={stored_transfer_syntax_uid}"
                    },
                )
            )


@receiver(post_delete, sender=DICOMImageSet)
def delete_image_set(*_, instance: DICOMImageSet, **__):
    from grandchallenge.cases.tasks import delete_health_imaging_image_set

    on_commit(
        delete_health_imaging_image_set.signature(
            kwargs={"image_set_id": instance.image_set_id}
        ).apply_async
    )


class Image(UUIDModel):
    COLOR_SPACE_GRAY = ColorSpace.GRAY.value
    COLOR_SPACE_RGB = ColorSpace.RGB.value
    COLOR_SPACE_RGBA = ColorSpace.RGBA.value
    COLOR_SPACE_YCBCR = ColorSpace.YCBCR.value

    COLOR_SPACES = (
        (COLOR_SPACE_GRAY, "GRAY"),
        (COLOR_SPACE_RGB, "RGB"),
        (COLOR_SPACE_RGBA, "RGBA"),
        (COLOR_SPACE_YCBCR, "YCBCR"),
    )

    COLOR_SPACE_COMPONENTS = {
        COLOR_SPACE_GRAY: 1,
        COLOR_SPACE_RGB: 3,
        COLOR_SPACE_RGBA: 4,
        COLOR_SPACE_YCBCR: 4,
    }

    EYE_OD = "OD"
    EYE_OS = "OS"
    EYE_UNKNOWN = "U"
    EYE_NA = "NA"
    EYE_CHOICES = (
        (EYE_OD, "Oculus Dexter (right eye)"),
        (EYE_OS, "Oculus Sinister (left eye)"),
        (EYE_UNKNOWN, "Unknown"),
        (EYE_NA, "Not applicable"),
    )

    STEREOSCOPIC_LEFT = "L"
    STEREOSCOPIC_RIGHT = "R"
    STEREOSCOPIC_UNKNOWN = "U"
    STEREOSCOPIC_EMPTY = None
    STEREOSCOPIC_CHOICES = (
        (STEREOSCOPIC_LEFT, "Left"),
        (STEREOSCOPIC_RIGHT, "Right"),
        (STEREOSCOPIC_UNKNOWN, "Unknown"),
        (STEREOSCOPIC_EMPTY, "Not applicable"),
    )

    FOV_1M = "F1M"
    FOV_2 = "F2"
    FOV_3M = "F3M"
    FOV_4 = "F4"
    FOV_5 = "F5"
    FOV_6 = "F6"
    FOV_7 = "F7"
    FOV_UNKNOWN = "U"
    FOV_EMPTY = None
    FOV_CHOICES = (
        (FOV_1M, FOV_1M),
        (FOV_2, FOV_2),
        (FOV_3M, FOV_3M),
        (FOV_4, FOV_4),
        (FOV_5, FOV_5),
        (FOV_6, FOV_6),
        (FOV_7, FOV_7),
        (FOV_UNKNOWN, "Unknown"),
        (FOV_EMPTY, "Not applicable"),
    )

    PATIENT_SEX_MALE = PatientSex.MALE.value
    PATIENT_SEX_FEMALE = PatientSex.FEMALE.value
    PATIENT_SEX_OTHER = PatientSex.OTHER.value
    PATIENT_SEX_CHOICES = (
        (PATIENT_SEX_MALE, "Male"),
        (PATIENT_SEX_FEMALE, "Female"),
        (PATIENT_SEX_OTHER, "Other"),
    )

    name = models.CharField(max_length=4096)
    origin = models.ForeignKey(
        to=RawImageUploadSession,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    modality = models.ForeignKey(
        ImagingModality, null=True, blank=True, on_delete=models.SET_NULL
    )

    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    depth = models.IntegerField(null=True, blank=True)
    voxel_width_mm = models.FloatField(null=True, blank=True)
    voxel_height_mm = models.FloatField(null=True, blank=True)
    voxel_depth_mm = models.FloatField(null=True, blank=True)
    timepoints = models.IntegerField(null=True, blank=True)
    resolution_levels = models.IntegerField(null=True, blank=True)
    window_center = models.FloatField(null=True, blank=True)
    window_width = models.FloatField(null=True, blank=True)
    color_space = models.CharField(
        max_length=5, blank=True, choices=COLOR_SPACES
    )
    patient_id = models.CharField(max_length=64, default="", blank=True)
    # Max length for patient_name is 5 * 64 + 4 = 324, as described for value
    # representation PN in the DICOM standard. See table at:
    # http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
    patient_name = models.CharField(max_length=324, default="", blank=True)
    patient_birth_date = models.DateField(null=True, blank=True)
    patient_age = models.CharField(max_length=4, default="", blank=True)
    patient_sex = models.CharField(
        max_length=1, blank=True, choices=PATIENT_SEX_CHOICES, default=""
    )
    study_date = models.DateField(null=True, blank=True)
    study_instance_uid = models.CharField(
        max_length=64, default="", blank=True
    )
    series_instance_uid = models.CharField(
        max_length=64, default="", blank=True
    )
    study_description = models.CharField(max_length=64, default="", blank=True)
    series_description = models.CharField(
        max_length=64, default="", blank=True
    )
    segments = models.JSONField(
        null=True,
        blank=True,
        default=None,
        validators=[JSONValidator(schema=SEGMENTS_SCHEMA)],
    )
    eye_choice = models.CharField(
        max_length=2,
        choices=EYE_CHOICES,
        default=EYE_NA,
        help_text="Is this (retina) image from the right or left eye?",
    )
    stereoscopic_choice = models.CharField(
        max_length=1,
        choices=STEREOSCOPIC_CHOICES,
        default=STEREOSCOPIC_EMPTY,
        null=True,
        blank=True,
        help_text="Is this the left or right image of a stereoscopic pair?",
    )
    field_of_view = models.CharField(
        max_length=3,
        choices=FOV_CHOICES,
        default=FOV_EMPTY,
        null=True,
        blank=True,
        help_text="What is the field of view of this image?",
    )
    dicom_image_set = models.OneToOneField(
        to=DICOMImageSet,
        editable=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name="image",
    )

    def __str__(self):
        return f"Image {self.name} {self.shape_without_color}"

    @property
    def title(self):
        return self.name

    @property
    def shape_without_color(self) -> list[int]:
        """
        Return the shape of the image without the color channel.

        Returns
        -------
            The shape of the image in NumPy ordering [(t), (z), y, x]
        """
        result = []
        if self.timepoints is not None:
            result.append(self.timepoints)
        if self.depth is not None:
            result.append(self.depth)
        result.append(self.height)
        result.append(self.width)
        return result

    @property
    def shape(self) -> list[int]:
        """
        Return the shape of the image with the color channel.

        Returns
        -------
            The shape of the image in NumPy ordering [(t), (z), y, x, (c)]
        """
        result = self.shape_without_color
        color_components = self.COLOR_SPACE_COMPONENTS[self.color_space]
        if color_components > 1:
            result.append(color_components)
        return result

    @property
    def _metaimage_files(self):
        """
        Return ImageFile objects for the related MHA file or MHD and RAW files.

        Returns
        -------
            Tuple of MHA/MHD ImageFile and optionally RAW ImageFile

        Raises
        ------
        FileNotFoundError
            Raised when Image has no related mhd/mha ImageFile or actual file
            cannot be found on storage
        """
        image_data_file = None
        try:
            header_file = self.files.get(
                image_type=ImageFile.IMAGE_TYPE_MHD, file__endswith=".mha"
            )
        except ObjectDoesNotExist:
            try:
                # Fallback to files that are still stored as mhd/(z)raw
                header_file = self.files.get(
                    image_type=ImageFile.IMAGE_TYPE_MHD, file__endswith=".mhd"
                )
                image_data_file = self.files.get(
                    image_type=ImageFile.IMAGE_TYPE_MHD, file__endswith="raw"
                )
            except ObjectDoesNotExist:
                raise FileNotFoundError(
                    f"No mhd or mha file found for image {self.name} (pk: {self.pk})"
                )

        if not header_file.file.storage.exists(name=header_file.file.name):
            raise FileNotFoundError(f"No file found for {header_file.file}")

        return header_file, image_data_file

    @property
    def sitk_image(self):
        """
        Return the image that belongs to this model instance as an SimpleITK image.

        Requires that exactly one MHD/RAW file pair is associated with the model.
        Otherwise it wil raise a MultipleObjectsReturned or ObjectDoesNotExist
        exception.

        Returns
        -------
            A SimpleITK image
        """
        files = [i for i in self._metaimage_files if i is not None]

        file_size = 0
        for file in files:
            if not file.file.storage.exists(name=file.file.name):
                raise FileNotFoundError(f"No file found for {file.file}")

            # Add up file sizes of mhd and raw file to get total file size
            file_size += file.file.size

        # Check file size to guard for out of memory error
        if file_size > settings.MAX_SITK_FILE_SIZE:
            raise OSError(
                f"File exceeds maximum file size. (Size: {file_size}, Max: {settings.MAX_SITK_FILE_SIZE})"
            )

        with TemporaryDirectory() as tempdirname:
            for file in files:
                with (
                    file.file.open("rb") as infile,
                    open(
                        Path(tempdirname) / Path(file.file.name).name, "wb"
                    ) as outfile,
                ):
                    buffer = True
                    while buffer:
                        buffer = infile.read(1024)
                        outfile.write(buffer)

            try:
                hdr_path = Path(tempdirname) / Path(files[0].file.name).name
                sitk_image = load_sitk_image(hdr_path)
            except RuntimeError as e:
                logging.error(
                    f"Failed to load SimpleITK image with error: {e}"
                )
                raise

        return sitk_image

    def update_viewer_groups_permissions(
        self,
        *,
        exclude_jobs=None,
        exclude_archive_items=None,
        exclude_display_sets=None,
    ):
        expected_groups = set()

        expected_groups.update(
            self._get_expected_job_viewer_groups(exclude_jobs=exclude_jobs)
        )

        expected_groups.update(
            self._get_expected_archive_item_viewer_groups(
                exclude_archive_items=exclude_archive_items
            )
        )

        expected_groups.update(
            self._get_expected_display_set_viewer_groups(
                exclude_display_sets=exclude_display_sets
            )
        )

        expected_groups.update(self._get_expected_reader_study_answer_groups())

        current_groups = get_groups_with_perms(self, attach_perms=True)
        current_groups = {
            group
            for group, perms in current_groups.items()
            if "view_image" in perms
        }

        groups_missing_perms = expected_groups - current_groups
        groups_with_extra_perms = current_groups - expected_groups

        for g in groups_missing_perms:
            assign_perm("view_image", g, self)

        for g in groups_with_extra_perms:
            remove_perm("view_image", g, self)

    def _get_expected_job_viewer_groups(self, exclude_jobs):
        from grandchallenge.algorithms.models import Job

        expected_groups = set()

        for key in ["inputs__image", "outputs__image"]:
            job_queryset = (
                Job.objects.filter(**{key: self})
                .prefetch_related("viewer_groups")
                .only("viewer_groups")
            )

            if exclude_jobs is not None:
                job_queryset = job_queryset.exclude(
                    pk__in={j.pk for j in exclude_jobs}
                )

            try:
                for job in job_queryset:
                    expected_groups.update(job.viewer_groups.all())
            except SoftTimeLimitExceeded as error:
                logger.error(error, exc_info=True)
                raise

        return expected_groups

    def _get_expected_archive_item_viewer_groups(
        self, *, exclude_archive_items
    ):
        from grandchallenge.archives.models import ArchiveItem

        expected_groups = set()

        archive_items_queryset = (
            ArchiveItem.objects.filter(values__image=self)
            .select_related(
                "archive__editors_group",
                "archive__uploaders_group",
                "archive__users_group",
            )
            .only(
                "archive__editors_group",
                "archive__uploaders_group",
                "archive__users_group",
            )
        )

        if exclude_archive_items is not None:
            archive_items_queryset = archive_items_queryset.exclude(
                pk__in={ai.pk for ai in exclude_archive_items}
            )

        for archive_item in archive_items_queryset:
            expected_groups.update(
                [
                    archive_item.archive.editors_group,
                    archive_item.archive.uploaders_group,
                    archive_item.archive.users_group,
                ]
            )

        return expected_groups

    def _get_expected_display_set_viewer_groups(self, *, exclude_display_sets):
        from grandchallenge.reader_studies.models import DisplaySet

        expected_groups = set()

        display_set_queryset = (
            DisplaySet.objects.filter(values__image=self)
            .select_related(
                "reader_study__editors_group",
                "reader_study__readers_group",
            )
            .only(
                "reader_study__editors_group",
                "reader_study__readers_group",
            )
        )

        if exclude_display_sets is not None:
            display_set_queryset = display_set_queryset.exclude(
                pk__in={ds.pk for ds in exclude_display_sets}
            )

        for display_set in display_set_queryset:
            expected_groups.update(
                [
                    display_set.reader_study.editors_group,
                    display_set.reader_study.readers_group,
                ]
            )

        return expected_groups

    def _get_expected_reader_study_answer_groups(self):
        # Reader study editors for reader studies that have answers that
        # include this image.

        expected_groups = set()

        for answer in self.answer_set.select_related(
            "question__reader_study__editors_group"
        ).all():
            expected_groups.add(answer.question.reader_study.editors_group)

        return expected_groups

    def assign_view_perm_to_creator(self):
        for answer in self.answer_set.all():
            assign_perm("view_image", answer.creator, self)

    @property
    def api_url(self) -> str:
        return reverse("api:image-detail", kwargs={"pk": self.pk})

    class Meta:
        ordering = ("name",)


@receiver(post_delete, sender=Image)
def delete_dicom_image_set(*_, instance: Image, **__):
    if instance.dicom_image_set:
        instance.dicom_image_set.delete()


class ImageUserObjectPermission(UserObjectPermissionBase):
    allowed_permissions = frozenset({"view_image"})

    content_object = models.ForeignKey(Image, on_delete=models.CASCADE)


class ImageGroupObjectPermission(GroupObjectPermissionBase):
    allowed_permissions = frozenset({"view_image"})

    content_object = models.ForeignKey(Image, on_delete=models.CASCADE)


class ImageFile(FieldChangeMixin, UUIDModel):
    IMAGE_TYPE_MHD = ImageType.MHD.value
    IMAGE_TYPE_TIFF = ImageType.TIFF.value
    IMAGE_TYPE_DZI = ImageType.DZI.value

    IMAGE_TYPES = (
        (IMAGE_TYPE_MHD, "MHD"),
        (IMAGE_TYPE_TIFF, "TIFF"),
        (IMAGE_TYPE_DZI, "DZI"),
    )

    image = models.ForeignKey(
        to=Image, null=True, on_delete=models.CASCADE, related_name="files"
    )
    image_type = models.CharField(
        max_length=4, blank=False, choices=IMAGE_TYPES, default=IMAGE_TYPE_MHD
    )
    file = models.FileField(
        upload_to=image_file_path,
        blank=False,
        storage=protected_s3_storage,
        max_length=200,
    )
    size_in_storage = models.PositiveBigIntegerField(
        editable=False,
        default=0,
        help_text="The number of bytes stored in the storage backend",
    )

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, **kwargs)

        if directory is not None:
            directory = directory.resolve()
            if not directory.is_dir():
                raise ValueError(f"{directory} is not a directory")

        self._directory = directory

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if self.initial_value("file") and self.has_changed("file"):
            raise RuntimeError("The file cannot be changed")

        if adding and self._directory is not None:
            self.save_directory()

        if adding or self.has_changed("file"):
            self.update_size_in_storage()

        super().save(*args, **kwargs)

    def _directory_file_destination(self, *, file):
        base = self.file.field.upload_to(
            instance=self, filename=f"{self._directory.stem}"
        )
        return safe_join(f"/{base}", file.relative_to(self._directory))[1:]

    def save_directory(self):
        # Saves all the files in the directory associated with this file
        if self._directory is None:
            raise ValueError("Directory is unset")

        for file in self._directory.rglob("**/*"):
            if not file.is_file():
                continue

            if file.is_symlink() or file.absolute() != file.resolve():
                raise SuspiciousFileOperation

            with open(file, "rb") as f:
                self.file.field.storage.save(
                    name=self._directory_file_destination(file=file), content=f
                )

    def update_size_in_storage(self):
        if not self.file:
            self.size_in_storage = 0
            return

        stored_bytes = self.file.size

        if self.image_type == self.IMAGE_TYPE_DZI:
            paginator = self.file.storage.connection.meta.client.get_paginator(
                "list_objects"
            )
            images_prefix = clean_name(
                self.file.name.replace(".dzi", "_files")
            )
            pages = paginator.paginate(
                Bucket=self.file.storage.bucket_name, Prefix=images_prefix
            )
            for page in pages:
                for entry in page.get("Contents", ()):
                    stored_bytes += entry["Size"]

        self.size_in_storage = stored_bytes


@receiver(post_delete, sender=ImageFile)
def delete_image_files(*_, instance: ImageFile, **__):
    """
    Deletes the related image files, note that DZI files are not handled!

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    if instance.file:
        instance.file.storage.delete(name=instance.file.name)


class PostProcessImageTaskStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", _("Initialized")
    CANCELLED = "CANCELLED", _("Cancelled")
    FAILED = "FAILED", _("Failed")
    COMPLETED = "COMPLETED", _("Completed")


class PostProcessImageTask(UUIDModel):
    image = models.OneToOneField(
        to=Image,
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=12,
        choices=PostProcessImageTaskStatusChoices.choices,
        blank=False,
        default=PostProcessImageTaskStatusChoices.INITIALIZED,
    )

    PostProcessImageTaskStatusChoices = PostProcessImageTaskStatusChoices

    class Meta:
        indexes = (
            models.Index(fields=["-created"]),
            models.Index(fields=["status"]),
        )
        constraints = (
            models.CheckConstraint(
                check=models.Q(
                    status__in=PostProcessImageTaskStatusChoices.values
                ),
                name="valid_post_process_image_task_status",
            ),
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            from grandchallenge.cases.tasks import (
                execute_post_process_image_task,
            )

            on_commit(
                execute_post_process_image_task.signature(
                    kwargs={"post_process_image_task_pk": self.pk}
                ).apply_async
            )


def generate_dicom_id_suffix(*, pk, suffix_type):
    """
    This value will be appended to the ROOT UID of the de-identifier,
    which is: "1.2.826.0.1.3680043.10.1666."

    The max length of a DICOM UID is 64 chars, and it can only contain
    numerical values and ".".

    That leaves a window of 36 chars for numerical values.
    An integer UUID is 39 characters, so cannot be used directly.

    Instead, we concatenate the pk with a suffix to differentiate
    the type (e.g., 'study' or 'series'). We then take the hash
    and convert it to an integer. Using the first 14 bytes
    of the hash will result in an integer with max length
    34 chars, fitting in to the available 36.
    """
    seed = f"{pk}-{suffix_type}"

    digest = hashlib.sha512(seed.encode("utf8")).digest()
    return str(int.from_bytes(digest[:14]))


class DICOMImageSetUploadStatusChoices(models.TextChoices):
    INITIALIZED = "INITIALIZED", _("Initialized")
    STARTED = "STARTED", _("Started")
    FAILED = "FAILED", _("Failed")
    COMPLETED = "COMPLETED", _("Completed")


@dataclass(config=ConfigDict(alias_generator=to_camel))
class ImageSetSummary:
    image_set_id: str
    image_set_version: int
    is_primary: bool
    number_of_matched_sop_instances: int = Field(
        alias="numberOfMatchedSOPInstances"
    )


@dataclass(config=ConfigDict(alias_generator=to_camel))
class JobSummary:
    job_id: str
    datastore_id: str
    input_s3_uri: str
    output_s3_uri: str
    success_output_s3_uri: str
    failure_output_s3_uri: str
    number_of_scanned_files: int
    number_of_imported_files: int
    number_of_files_with_customer_error: int
    number_of_files_with_server_error: int
    number_of_generated_image_sets: int
    image_sets_summary: list[ImageSetSummary]

    @field_validator("image_sets_summary", mode="before")
    @classmethod
    def convert_image_set_summaries(cls, data):
        return [
            ImageSetSummary(**image_set_summary_data)
            for image_set_summary_data in data
        ]


class DICOMImageSetUpload(UUIDModel):
    DICOMImageSetUploadStatusChoices = DICOMImageSetUploadStatusChoices

    creator = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
    )
    user_uploads = models.ManyToManyField(
        UserUpload, blank=True, related_name="dicom_image_set_uploads"
    )
    status = models.CharField(
        max_length=11,
        choices=DICOMImageSetUploadStatusChoices.choices,
        default=DICOMImageSetUploadStatusChoices.INITIALIZED,
        blank=False,
    )
    error_message = models.TextField(editable=False, default="")
    internal_failure_log = models.JSONField(
        default=list,
        editable=False,
        help_text="Contents of failure.ndjson from the health imaging "
        "import job if the job failed or did not pass validation.",
        validators=[JSONValidator(schema=IMPORT_JOB_FAILURE_NDJSON_SCHEMA)],
    )
    study_instance_uid = models.CharField(
        max_length=36,
        editable=False,
        unique=True,
    )
    series_instance_uid = models.CharField(
        max_length=36,
        editable=False,
        unique=True,
    )
    name = models.CharField(
        max_length=255, help_text="The name for the resulting Image instance"
    )
    task_on_success = models.JSONField(
        default=None,
        null=True,
        editable=False,
        help_text="Serialized task that is run on job success",
    )

    class Meta:
        verbose_name = "DICOM image set upload"
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    status__in=DICOMImageSetUploadStatusChoices.values
                ),
                name="dicomuimagesetupload_status_valid",
            )
        ]
        indexes = (models.Index(fields=["status"]),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__health_imaging_client = None
        self.__s3_client = None

    def save(self, *args, **kwargs):
        adding = self._state.adding

        self.study_instance_uid = generate_dicom_id_suffix(
            pk=self.pk, suffix_type="study"
        )
        self.series_instance_uid = generate_dicom_id_suffix(
            pk=self.pk, suffix_type="series"
        )

        super().save(*args, **kwargs)

        if adding:
            if self.creator:
                follow(
                    user=self.creator,
                    obj=self,
                    send_action=False,
                    actor_only=False,
                )

    @property
    def _s3_client(self):
        if self.__s3_client is None:
            self.__s3_client = boto3.client(
                "s3",
                region_name=settings.AWS_DEFAULT_REGION,
            )
        return self.__s3_client

    @property
    def _health_imaging_client(self):
        if self.__health_imaging_client is None:
            self.__health_imaging_client = boto3.client(
                "medical-imaging",
                region_name=settings.AWS_DEFAULT_REGION,
            )
        return self.__health_imaging_client

    @property
    def _import_job_name(self):
        # Health Imaging requires job names to be max 64 chars
        return f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self.pk}"

    @property
    def _input_prefix(self):
        return f"inputs/{self.pk}"

    @property
    def _import_input_s3_uri(self):
        return f"s3://{settings.AWS_HEALTH_IMAGING_BUCKET_NAME}/{self._input_prefix}"

    @property
    def _import_output_s3_uri(self):
        return f"s3://{settings.AWS_HEALTH_IMAGING_BUCKET_NAME}/logs/{self.pk}"

    @property
    def _marker_file_key(self):
        return f"{self._input_prefix}/deidentification.done"

    def mark_failed(
        self, *, error_message, detailed_error_message=None, exc=None
    ):
        self.status = DICOMImageSetUploadStatusChoices.FAILED

        if detailed_error_message:
            notification_description = oxford_comma(
                [
                    f"Image validation for socket {key} failed with error: {val}"
                    for key, val in detailed_error_message.items()
                ]
            )
        else:
            notification_description = error_message

        self.error_message = notification_description
        self.save()
        if exc:
            logger.error(exc, exc_info=True)
        Notification.send(
            kind=NotificationTypeChoices.IMAGE_IMPORT_STATUS,
            description=notification_description,
            action_object=self,
        )

    def start_dicom_import_job(self):
        return self._health_imaging_client.start_dicom_import_job(
            jobName=self._import_job_name,
            datastoreId=settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
            dataAccessRoleArn=settings.AWS_HEALTH_IMAGING_IMPORT_ROLE_ARN,
            inputS3Uri=self._import_input_s3_uri,
            outputS3Uri=self._import_output_s3_uri,
        )

    def _get_image_set_metadata(self, *, image_set_id):
        response = self._health_imaging_client.get_image_set_metadata(
            datastoreId=settings.AWS_HEALTH_IMAGING_DATASTORE_ID,
            imageSetId=image_set_id,
            versionId="1",
        )

        metadata = json.loads(
            gzip.decompress(response["imageSetMetadataBlob"].read())
        )

        return metadata

    def _get_image_frame_metadata(self, *, image_set_id):
        metadata = self._get_image_set_metadata(image_set_id=image_set_id)

        return [
            {
                "study_instance_uid": metadata["Study"]["DICOM"][
                    "StudyInstanceUID"
                ],
                "series_instance_uid": series["DICOM"]["SeriesInstanceUID"],
                "sop_instance_uid": instance["DICOM"]["SOPInstanceUID"],
                "stored_transfer_syntax_uid": instance[
                    "StoredTransferSyntaxUID"
                ],
                "image_frame_id": frame["ID"],
                "frame_size_in_bytes": frame["FrameSizeInBytes"],
            }
            for series in metadata["Study"]["Series"].values()
            for instance in series["Instances"].values()
            for frame in instance["ImageFrames"]
        ]

    def _deidentify_files(self):
        deid = DicomDeidentifier(
            study_instance_uid_suffix=self.study_instance_uid,
            series_instance_uid_suffix=self.series_instance_uid,
            assert_unique_value_for=[
                "StudyInstanceUID",
                "SeriesInstanceUID",
                "PatientID",
                "StudyID",
                "StudyDate",
                "AccessionNumber",
                "SeriesNumber",
            ],
        )
        for upload in self.user_uploads.all():
            with (
                SpooledTemporaryFile() as infile,
                SpooledTemporaryFile() as outfile,
            ):
                self._s3_client.download_fileobj(
                    Fileobj=infile,
                    Bucket=upload.bucket,
                    Key=upload.key,
                )
                infile.seek(0)

                deid.deidentify_file(infile, output=outfile)

                outfile.seek(0)
                self._s3_client.upload_fileobj(
                    Fileobj=outfile,
                    Bucket=settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
                    Key=f"{self._input_prefix}/{upload.pk}.dcm",
                )

    def deidentify_user_uploads(self):
        # Check if marker file exists
        try:
            self._s3_client.head_object(
                Bucket=settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
                Key=self._marker_file_key,
            )
            logger.info("Deidentification already done, nothing to do.")
            return
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                # unexpected error
                raise

        self._deidentify_files()

        # Create empty marker file to indicate success
        self._s3_client.put_object(
            Bucket=settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
            Key=self._marker_file_key,
            Body=b"",
        )

        self.user_uploads.all().delete()

    def delete_input_files(self):
        from grandchallenge.components.backends.base import (
            list_and_delete_objects_from_prefix,
        )

        list_and_delete_objects_from_prefix(
            s3_client=self._s3_client,
            bucket=settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
            prefix=self._input_prefix,
        )

    def get_job_summary(self, *, event):
        output_uri = event["outputS3Uri"]
        parsed = urlparse(output_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/") + "job-output-manifest.json"

        obj = self._s3_client.get_object(Bucket=bucket, Key=key)

        return JobSummary(**json.load(obj["Body"])["jobSummary"])

    def get_job_output_failure_log(self, *, job_summary):
        output_uri = job_summary.failure_output_s3_uri
        parsed = urlparse(output_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/") + "failure.ndjson"

        obj = self._s3_client.get_object(Bucket=bucket, Key=key)

        return [json.loads(line) for line in obj["Body"].iter_lines()]

    def handle_event(self, *, event):
        try:
            job_status = event["jobStatus"]
            job_summary = self.get_job_summary(event=event)
            if job_status == "COMPLETED":
                self.handle_completed_job(job_summary=job_summary)
            elif job_status == "FAILED":
                self.handle_failed_job(job_summary=job_summary)
            else:
                raise ValueError("Invalid job status")
        except Exception as e:
            self.mark_failed(
                error_message="An unexpected error occurred", exc=e
            )
        else:
            self.status = self.DICOMImageSetUploadStatusChoices.COMPLETED
            self.save()
            self.execute_task_on_success()
        finally:
            self.delete_input_files()

    def handle_completed_job(self, *, job_summary):
        self.validate_image_set(job_summary=job_summary)
        image_set_id = job_summary.image_sets_summary[0].image_set_id
        self.convert_image_set_to_internal(image_set_id=image_set_id)

    def validate_image_set(self, *, job_summary):
        if (
            job_summary.number_of_files_with_customer_error != 0
            or job_summary.number_of_files_with_server_error != 0
            or job_summary.number_of_generated_image_sets == 0
        ):
            self.handle_failed_job(job_summary=job_summary)
        elif job_summary.number_of_generated_image_sets > 1:
            self.delete_image_sets(job_summary=job_summary)
            raise RuntimeError(
                "Multiple image sets created. Expected only one."
            )

        image_set_summary = job_summary.image_sets_summary[0]

        if not image_set_summary.is_primary:
            self.delete_image_sets(job_summary=job_summary)
            raise RuntimeError(
                "New instance is not primary: "
                "metadata conflicts with already existing instance."
            )

        if not image_set_summary.image_set_version == 1:
            self.revert_image_set_to_initial_version(
                image_set_summary=image_set_summary
            )
            raise RuntimeError(
                "Instance already exists. This should never happen!"
            )

    def handle_failed_job(self, *, job_summary):
        self.internal_failure_log = self.get_job_output_failure_log(
            job_summary=job_summary
        )
        self.delete_image_sets(job_summary=job_summary)
        raise RuntimeError(
            f"Import job {job_summary.job_id} failed for DICOMImageSetUpload {self.pk}"
        )

    @staticmethod
    def delete_image_sets(*, job_summary):
        from grandchallenge.cases.tasks import delete_health_imaging_image_set

        for image_set_summary in job_summary.image_sets_summary:
            on_commit(
                delete_health_imaging_image_set.signature(
                    kwargs={"image_set_id": image_set_summary.image_set_id}
                ).apply_async
            )

    @staticmethod
    def revert_image_set_to_initial_version(*, image_set_summary):
        from grandchallenge.cases.tasks import (
            revert_image_set_to_initial_version,
        )

        on_commit(
            revert_image_set_to_initial_version.signature(
                kwargs={
                    "image_set_id": image_set_summary.image_set_id,
                    "version_id": image_set_summary.image_set_version,
                }
            ).apply_async
        )

    def convert_image_set_to_internal(self, *, image_set_id):
        dicom_image_set = DICOMImageSet(
            image_set_id=image_set_id,
            image_frame_metadata=self._get_image_frame_metadata(
                image_set_id=image_set_id
            ),
            dicom_image_set_upload=self,
        )
        dicom_image_set.full_clean()
        dicom_image_set.save()

        image = Image(dicom_image_set=dicom_image_set, name=self.name)
        image.full_clean()
        image.save()

    def execute_task_on_success(self):
        if self.task_on_success:
            on_commit(signature(self.task_on_success).apply_async)
