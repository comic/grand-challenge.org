import os

import boto3
from django.conf import settings
from django.db import models
from django.db.models import SET_NULL
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.datetime_safe import strftime
from django.utils.text import get_valid_filename
from django.utils.timezone import now
from django_summernote.models import AbstractAttachment
from guardian.shortcuts import assign_perm

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


class UserUpload(UUIDModel):
    LIST_MAX_ITEMS = 1000

    class StatusChoices(models.IntegerChoices):
        PENDING = 0, "Pending"
        INITIALIZED = 1, "Initialized"
        COMPLETED = 2, "Completed"
        ABORTED = 3, "Aborted"

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    filename = models.CharField(max_length=128)
    status = models.PositiveSmallIntegerField(
        choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    s3_upload_id = models.CharField(max_length=128, blank=True)

    class Meta(UUIDModel.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__client = None

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_multipart_upload()

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    @property
    def _client(self):
        if self.__client is None:
            self.__client = boto3.client(
                "s3", endpoint_url=settings.UPLOADS_S3_ENDPOINT_URL
            )
        return self.__client

    @property
    def bucket(self):
        return settings.UPLOADS_S3_BUCKET_NAME

    @property
    def key(self):
        # There are several assumptions about the structure of this key
        # elsewhere in the codebase and in clients code
        # First for grouping by the user
        # Second for where the UserUpload pk appears in the key
        # Change with extreme caution
        return f"{self.creators_key_prefix}{self.pk}"

    @property
    def creators_key_prefix(self):
        # Prefix to objects that the user has uploaded
        # Do not change this
        return f"uploads/{self.creator.pk}/"

    @property
    def size_of_creators_completed_uploads(self):
        return sum(u["Size"] for u in self.get_creators_completed_uploads())

    def get_creators_completed_uploads(self, continuation_token=None):
        kwargs = {
            "Bucket": self.bucket,
            "Prefix": self.creators_key_prefix,
            "MaxKeys": self.LIST_MAX_ITEMS,
        }

        if continuation_token is not None:
            kwargs["ContinuationToken"] = continuation_token

        response = self._client.list_objects_v2(**kwargs)

        objects = response.get("Contents", [])

        if response["IsTruncated"]:
            objects += self.get_creators_completed_uploads(
                continuation_token=response["NextContinuationToken"]
            )

        return objects

    def assign_permissions(self):
        assign_perm("view_userupload", self.creator, self)
        assign_perm("change_userupload", self.creator, self)

    def create_multipart_upload(self):
        if self.status != self.StatusChoices.PENDING:
            raise RuntimeError("Upload is not pending")

        response = self._client.create_multipart_upload(
            Bucket=settings.UPLOADS_S3_BUCKET_NAME, Key=self.key,
        )
        self.s3_upload_id = response["UploadId"]
        self.status = self.StatusChoices.INITIALIZED

    def generate_presigned_urls(self, *, part_numbers):
        return {
            str(part_number): self.generate_presigned_url(
                part_number=part_number
            )
            for part_number in part_numbers
        }

    def generate_presigned_url(self, *, part_number):
        if self.status != self.StatusChoices.INITIALIZED:
            raise RuntimeError("Upload is not initialized")

        return self._client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self.bucket,
                "Key": self.key,
                "UploadId": self.s3_upload_id,
                "PartNumber": part_number,
            },
        )

    def list_parts(self, *, part_number_marker=0):
        if self.status != self.StatusChoices.INITIALIZED:
            raise RuntimeError("Upload is not initialized")

        response = self._client.list_parts(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.s3_upload_id,
            MaxParts=self.LIST_MAX_ITEMS,
            PartNumberMarker=part_number_marker,
        )

        parts = response.get("Parts", [])

        if response["IsTruncated"]:
            parts += self.list_parts(
                part_number_marker=response["NextPartNumberMarker"]
            )

        return parts

    def complete_multipart_upload(self, *, parts):
        if self.status != self.StatusChoices.INITIALIZED:
            raise RuntimeError("Upload is not initialized")

        self._client.complete_multipart_upload(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.s3_upload_id,
            MultipartUpload={"Parts": parts},
        )
        self.status = self.StatusChoices.COMPLETED

    def abort_multipart_upload(self):
        if self.status != self.StatusChoices.INITIALIZED:
            raise RuntimeError("Upload is not initialized")

        self._client.abort_multipart_upload(
            Bucket=self.bucket, Key=self.key, UploadId=self.s3_upload_id,
        )
        self.s3_upload_id = ""
        self.status = self.StatusChoices.ABORTED

    def delete_object(self):
        if self.status != self.StatusChoices.COMPLETED:
            raise RuntimeError("Upload is not completed")

        self._client.delete_object(Bucket=self.bucket, Key=self.key)
        self.status = self.StatusChoices.ABORTED


@receiver(post_delete, sender=UserUpload)
def delete_objects_hook(*_, instance: UserUpload, **__):
    """
    Deletes the objects from storage.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    if instance.status == UserUpload.StatusChoices.COMPLETED:
        instance.delete_object()
    elif instance.status == UserUpload.StatusChoices.INITIALIZED:
        instance.abort_multipart_upload()
