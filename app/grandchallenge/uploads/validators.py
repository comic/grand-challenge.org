from django.core.exceptions import ValidationError

from grandchallenge.uploads.models import UserUpload


def validate_gzip_mimetype(value):
    try:
        user_upload = UserUpload.objects.get(
            pk=value, status=UserUpload.StatusChoices.COMPLETED
        )
    except UserUpload.DoesNotExist:
        raise ValidationError("This upload does not exist")

    if user_upload.mimetype not in {"application/gzip", "application/x-gzip"}:
        raise ValidationError("This upload is not a valid .tar.gz file")
