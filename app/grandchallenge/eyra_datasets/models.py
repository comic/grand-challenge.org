import logging, re
from .types import types

from compat import URLValidator
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.core.models import UUIDModel

from django.core.files.storage import Storage, FileSystemStorage

logger = logging.getLogger(__name__)


class EyraDataSet(UUIDModel):
    TYPES = {type.name: type for type in types}

    ACCESS_PRIVATE = "private"
    ACCESS_PUBLIC = "public"

    ACCESS_TYPES = ((ACCESS_PRIVATE, "Private"), (ACCESS_PUBLIC, "Public"))

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="eyra_datasets",
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20, null=False, blank=False)
    type = models.CharField(
        choices=[(type.name, type.verbose_name) for type in types],
        max_length=20,
    )
    frozen = models.BooleanField(default=False)

    def get_type_class(self):
        return self.TYPES[self.type]

    # access_type = models.CharField(
    #     max_length=8,
    #     null=False,
    #     blank=False,
    #     choices=ACCESS_TYPES,
    # )


@receiver(post_save, sender=EyraDataSet)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        type_class = instance.get_type_class()
        for file in type_class.files:
            new_file = EyraDataSetFile(
                role=file,
                dataset=instance,
            )
            new_file.save()


class EyraDataSetFileStorage(FileSystemStorage):
    # todo: make this S3/Minio/DO Spaces storage or something
    pass


class EyraDataSetFile(UUIDModel):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    dataset = models.ForeignKey(
        to=EyraDataSet, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(storage=EyraDataSetFileStorage, blank=True)
    role = models.CharField(max_length=40)
    sha = models.CharField(max_length=40, null=True, blank=True)
