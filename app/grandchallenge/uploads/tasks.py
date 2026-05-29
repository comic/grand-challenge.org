from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.uploads.models import UserUpload


@acks_late_micro_short_task(name=f"{__name__}.delete_old_user_uploads")
@transaction.atomic
def delete_old_user_uploads_celery(**kwargs):
    # TODO: 4408 Remove, this is still here to handle existing tasks on SQS
    return delete_old_user_uploads(**kwargs)


@lambda_task
def delete_old_user_uploads():
    UserUpload.objects.filter(
        created__lt=now() - timedelta(days=settings.UPLOADS_TIMEOUT_DAYS)
    ).only("pk", "status", "creator_id", "s3_upload_id").delete()
