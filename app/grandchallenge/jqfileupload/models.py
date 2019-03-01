import os

from django.conf import settings
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
    client_id = models.CharField(max_length=128, null=True)
    client_filename = models.CharField(max_length=128, blank=False)
    file_id = models.UUIDField(blank=False)
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
