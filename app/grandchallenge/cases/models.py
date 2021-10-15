import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Mapping, Union

from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_delete, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from django.utils.text import get_valid_filename
from guardian.shortcuts import assign_perm, get_groups_with_perms, remove_perm
from panimg.image_builders.metaio_utils import (
    load_sitk_image,
    parse_mh_header,
)
from panimg.models import ColorSpace, ImageType, PatientSex

from grandchallenge.core.models import UUIDModel
from grandchallenge.core.storage import protected_s3_storage
from grandchallenge.modalities.models import ImagingModality
from grandchallenge.subdomains.utils import reverse
from grandchallenge.uploads.models import UserUpload

logger = logging.getLogger(__name__)


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
        UserUpload, blank=True, related_name="image_upload_sessions",
    )

    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=PENDING, db_index=True
    )

    import_result = models.JSONField(
        blank=True, null=True, default=None, editable=False
    )

    error_message = models.TextField(blank=False, null=True, default=None)

    def __str__(self):
        return (
            f"Upload Session <{str(self.pk).split('-')[0]}>, "
            f"({self.get_status_display()}) "
            f"{self.error_message or ''}"
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

    def process_images(self, linked_task=None):
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

        kwargs = {"upload_session_pk": self.pk}
        workflow = build_images.signature(kwargs=kwargs)

        if linked_task is not None:
            linked_task.kwargs.update(kwargs)
            workflow |= linked_task

        on_commit(workflow.apply_async)

    def get_absolute_url(self):
        return reverse(
            "cases:raw-image-upload-session-detail", kwargs={"pk": self.pk}
        )

    @property
    def api_url(self):
        return reverse("api:upload-session-detail", kwargs={"pk": self.pk})


@receiver(pre_delete, sender=RawImageUploadSession)
def delete_session_follows(*_, instance: RawImageUploadSession, **__):
    """
    Deletes the related follows.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()


class RawImageFile(UUIDModel):
    """
    A raw image file is a file that has been uploaded by a user but was not
    preprocessed to create a standardized image representation.
    """

    upload_session = models.ForeignKey(
        RawImageUploadSession, blank=False, on_delete=models.CASCADE
    )

    # Copy in case staged_file_id is set to None
    filename = models.CharField(max_length=4096, blank=False)

    staged_file_id = models.UUIDField(blank=True, null=True)

    error = models.TextField(blank=False, null=True, default=None)

    consumed = models.BooleanField(default=False)

    @property
    def creator(self):
        return self.upload_session.creator

    @property
    def api_url(self):
        return reverse(
            "api:upload-session-file-detail", kwargs={"pk": self.pk}
        )

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding and self.upload_session.creator:
            assign_perm(
                f"view_{self._meta.model_name}",
                self.upload_session.creator,
                self,
            )


def image_file_path(instance, filename):
    return (
        f"{settings.IMAGE_FILES_SUBDIRECTORY}/"
        f"{str(instance.image.pk)[0:2]}/"
        f"{str(instance.image.pk)[2:4]}/"
        f"{instance.image.pk}/"
        f"{get_valid_filename(filename)}"
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
        ImagingModality, null=True, blank=True, on_delete=models.SET_NULL,
    )

    width = models.IntegerField(blank=False)
    height = models.IntegerField(blank=False)
    depth = models.IntegerField(null=True, blank=True)
    voxel_width_mm = models.FloatField(null=True, blank=True)
    voxel_height_mm = models.FloatField(null=True, blank=True)
    voxel_depth_mm = models.FloatField(null=True, blank=True)
    timepoints = models.IntegerField(null=True, blank=True)
    resolution_levels = models.IntegerField(null=True, blank=True)
    window_center = models.FloatField(null=True, blank=True)
    window_width = models.FloatField(null=True, blank=True)
    color_space = models.CharField(
        max_length=5, blank=False, choices=COLOR_SPACES
    )
    patient_id = models.CharField(max_length=64, default="", blank=True)
    # Max length for patient_name is 5 * 64 + 4 = 324, as described for value
    # representation PN in the DICOM standard. See table at:
    # http://dicom.nema.org/medical/dicom/current/output/chtml/part05/sect_6.2.html
    patient_name = models.CharField(max_length=324, default="", blank=True)
    patient_birth_date = models.DateField(null=True, blank=True)
    patient_age = models.CharField(max_length=4, default="", blank=True)
    patient_sex = models.CharField(
        max_length=1, blank=True, choices=PATIENT_SEX_CHOICES, default="",
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

    def __str__(self):
        return f"Image {self.name} {self.shape_without_color}"

    @property
    def shape_without_color(self) -> List[int]:
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
    def shape(self) -> List[int]:
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
    def spacing(self) -> List[float]:
        """
        Return the voxel spacing (or size if spacing is nonexistent) of the image.

        Returns
        -------
            The voxel spacing in mm in NumPy ordering [(z), y, x]
            Defaults to [(1), 1, 1]
        """
        spacing = [
            self.voxel_depth_mm,
            self.voxel_height_mm,
            self.voxel_width_mm,
        ]
        if spacing[0] is None:
            spacing = spacing[-2:]
        if None in spacing:
            mh_header = self.get_mh_header()
            spacing_str = mh_header.get(
                "ElementSpacing", mh_header.get("ElementSize")
            )
            if spacing_str is not None:
                spacing = list(
                    reversed([float(x) for x in spacing_str.split(" ")])
                )
            else:
                spacing = [1] * int(mh_header["NDims"])
        return spacing

    def get_metaimage_files(self):
        """
        Return ImageFile object for the related MHA file or MHD and RAW files.

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

    def get_mh_header(self) -> Mapping[str, Union[str, None]]:
        """
        Return header from mhd/mha file as key value pairs

        Returns
        -------
            MetaIO headers as key value pairs.

        Raises
        ------
        FileNotFoundError
            Raised when Image has no related mhd/mha ImageFile or actual file
            cannot be found on storage
        """

        mh_file, _ = self.get_metaimage_files()
        return parse_mh_header(mh_file.file)

    def get_sitk_image(self):
        """
        Return the image that belongs to this model as an SimpleITK image.

        Requires that exactly one MHD/RAW file pair is associated with the model.
        Otherwise it wil raise a MultipleObjectsReturned or ObjectDoesNotExist
        exception.

        Returns
        -------
            A SimpleITK image
        """
        files = [i for i in self.get_metaimage_files() if i is not None]

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
                with file.file.open("rb") as infile, open(
                    Path(tempdirname) / Path(file.file.name).name, "wb"
                ) as outfile:
                    buffer = True
                    while buffer:
                        buffer = infile.read(1024)
                        outfile.write(buffer)

            try:
                hdr_path = Path(tempdirname) / Path(files[0].file.name).name
                sitk_image = load_sitk_image(mhd_file=hdr_path)
            except RuntimeError as e:
                logging.error(
                    f"Failed to load SimpleITK image with error: {e}"
                )
                raise

        return sitk_image

    def permit_viewing_by_retina_users(self):
        """Set object level view permissions for retina_graders and retina_admins."""
        for group_name in (
            settings.RETINA_GRADERS_GROUP_NAME,
            settings.RETINA_ADMINS_GROUP_NAME,
        ):
            group = Group.objects.get(name=group_name)
            assign_perm("view_image", group, self)

    def update_viewer_groups_permissions(self, *, exclude_jobs=None):
        """
        Update the permissions for the algorithm jobs viewers groups to
        view this image.

        Parameters
        ----------
        exclude_jobs
            Exclude these results from being considered. This is useful
            when a many to many relationship is being cleared to remove this
            image from the results image set, and is used when the pre_clear
            signal is sent.
        """
        from grandchallenge.archives.models import Archive

        if exclude_jobs is None:
            exclude_jobs = []

        algorithm_jobs_groups = (
            Q(job__inputs__image=self) | Q(job__outputs__image=self)
        ) & ~Q(job__in=exclude_jobs)
        reader_studies_groups = Q(
            editors_of_readerstudy__images__id__exact=self.pk
        ) | Q(readers_of_readerstudy__images__id__exact=self.pk)

        expected_groups = {
            *Group.objects.filter(algorithm_jobs_groups),
            *Group.objects.filter(reader_studies_groups),
        }

        for archive in Archive.objects.filter(
            items__values__image=self
        ).select_related("editors_group", "uploaders_group", "users_group"):
            expected_groups.update(
                [
                    archive.editors_group,
                    archive.uploaders_group,
                    archive.users_group,
                ]
            )

        # Reader study editors for reader studies that have answers that
        # include this image.
        for answer in self.answer_set.select_related(
            "question__reader_study__editors_group"
        ).all():
            expected_groups.add(answer.question.reader_study.editors_group)

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

    def assign_view_perm_to_creator(self):
        for answer in self.answer_set.all():
            assign_perm("view_image", answer.creator, self)

    @property
    def api_url(self):
        return reverse("api:image-detail", kwargs={"pk": self.pk})

    class Meta:
        ordering = ("name",)


class ImageFile(UUIDModel):
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
        upload_to=image_file_path, blank=False, storage=protected_s3_storage
    )


@receiver(post_delete, sender=ImageFile)
def delete_image_files(*_, instance: ImageFile, **__):
    """
    Deletes the related image files, note that DZI files are not handled!

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    instance.file.storage.delete(name=instance.file.name)


class FolderUpload:
    def __init__(self, image_id, folder):
        self.image_id = image_id
        self.folder = folder

    def full_clean(self):
        """Required as this is treated like a django model"""
        pass

    def destination_filename(self, file_path):
        return (
            f"{settings.IMAGE_FILES_SUBDIRECTORY}/"
            f"{str(self.image_id)[0:2]}/"
            f"{str(self.image_id)[2:4]}/"
            f"{self.image_id}/"
            f"{file_path.parent.parent.stem}/"
            f"{file_path.parent.stem}/"
            f"{file_path.name}"
        )

    def save(self):
        # Saves all the files in the folder, respecting the parents folder structure
        # 2 directories deep
        for root, _, files in os.walk(self.folder):
            for file in files:
                source_filename = Path(root) / file
                destination_filename = self.destination_filename(
                    source_filename
                )
                with open(source_filename, "rb") as open_file:
                    protected_s3_storage.save(destination_filename, open_file)
