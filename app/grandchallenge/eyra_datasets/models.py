import logging, re

from compat import URLValidator
from django.conf import settings
from django.db import models

from grandchallenge.core.models import UUIDModel

from django.core.files.storage import Storage, FileSystemStorage


logger = logging.getLogger(__name__)


class DataSetStorage(FileSystemStorage):
    # todo: make this S3/Minio/DO Spaces storage or something
    pass


class DataType(UUIDModel):
    name = models.CharField(max_length=20, null=False, blank=False)


class EyraDataSet(UUIDModel):
    ACCESS_PRIVATE = "private"
    ACCESS_PUBLIC = "public"

    ACCESS_TYPES = (
        (ACCESS_PRIVATE, "Private"),
        (ACCESS_PUBLIC, "Public"),
    )

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name='eyra_datasets'
    )
    created = models.DateTimeField(
        auto_now_add=True,
    )
    modified = models.DateTimeField(
        auto_now=True,
    )
    name = models.CharField(
        max_length=20,
        null=False,
        blank=False,
    )
    doi = models.CharField(
        null=True,
        blank=True,
        validators=[URLValidator(schemes=['http', 'https'])]
    )
    type = models.ForeignKey(
        to=DataType,
        on_delete=models.SET_NULL,
    )
    file = models.FileField(
        storage=DataSetStorage,
        blank=True,
    )
    access_type = models.CharField(
        max_length=8,
        null=False,
        blank=False,
        choices=ACCESS_TYPES,
    )
