import os

from django.conf import settings
from django.utils.text import get_valid_filename


def generate_upload_filename(instance, filename):
    return os.path.join(
        settings.JQFILEUPLOAD_UPLOAD_SUBIDRECTORY,
        f"{instance.file_id}",
        get_valid_filename(
            f"{instance.start_byte}-{instance.end_byte}-{filename}"
        ),
    )
