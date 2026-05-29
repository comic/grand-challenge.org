from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.uploads.models import UserUpload


@lambda_task
def delete_old_user_uploads():
    UserUpload.objects.filter(
        created__lt=now() - timedelta(days=settings.UPLOADS_TIMEOUT_DAYS)
    ).only("pk", "status", "creator_id", "s3_upload_id").delete()
