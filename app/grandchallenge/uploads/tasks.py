from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from grandchallenge.core.celery import acks_late_micro_short_task
from grandchallenge.uploads.models import UserUpload


@acks_late_micro_short_task
@transaction.atomic
def delete_old_user_uploads():
    UserUpload.objects.filter(
        created__lt=now() - timedelta(days=settings.UPLOADS_TIMEOUT_DAYS)
    ).only("pk").delete()
