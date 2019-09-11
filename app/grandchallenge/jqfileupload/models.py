import os
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.core.storage import private_s3_storage


def generate_upload_filename(instance, filename):
    return os.path.join(
        settings.JQFILEUPLOAD_UPLOAD_SUBIDRECTORY,
        f"{instance.file_id}",
        filename,
    )


class StagedFile(models.Model):
    """
    Files uploaded but not committed to other forms.
    """

    csrf = models.CharField(max_length=128)
    client_id = models.CharField(max_length=128, null=True, blank=True)
    client_filename = models.CharField(max_length=128, blank=False)
    file_id = models.UUIDField(blank=False, default=uuid4)
    timeout = models.DateTimeField(blank=False)
    file = models.FileField(
        blank=False,
        max_length=256,
        upload_to=generate_upload_filename,
        storage=private_s3_storage,
    )
    start_byte = models.BigIntegerField(blank=False)
    end_byte = models.BigIntegerField(blank=False)
    total_size = models.BigIntegerField(null=True)

    # Support for disambiguating between different upload widgets on the same
    # website
    upload_path_sha256 = models.CharField(max_length=64)

    @property
    def is_chunked(self):
        return not (
            self.start_byte == 0 and self.end_byte == self.total_size - 1
        )

    def clean(self):
        if self.start_byte > self.end_byte:
            raise ValidationError("Supplied invalid Content-Range")

        if (self.total_size is not None) and (
            self.end_byte >= self.total_size
        ):
            raise ValidationError("End byte exceeds total file size")

        if self.end_byte - self.start_byte + 1 != self.file.size:
            raise ValidationError("Invalid start-end byte range")

        if self.is_chunked:
            # Verify consistency and generate file ids
            other_chunks = StagedFile.objects.filter(
                csrf=self.csrf,
                client_id=self.client_id,
                upload_path_sha256=self.upload_path_sha256,
            ).all()
            if other_chunks.exists():
                chunk_intersects = other_chunks.filter(
                    start_byte__lte=self.end_byte,
                    end_byte__gte=self.start_byte,
                ).exists()
                if chunk_intersects:
                    raise ValidationError("Overlapping chunks")

                inconsistent_filenames = other_chunks.exclude(
                    client_filename=self.client_filename
                ).exists()
                if inconsistent_filenames:
                    raise ValidationError("Chunks have inconsistent filenames")

                if self.total_size is not None:
                    inconsistent_total_size = (
                        other_chunks.exclude(total_size=None)
                        .exclude(total_size=self.total_size)
                        .exists()
                    )
                    if inconsistent_total_size:
                        raise ValidationError("Inconsistent total size")

                self.file_id = other_chunks[0].file_id
