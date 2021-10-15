from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

from grandchallenge.uploads.models import UserUpload


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def delete_old_user_uploads():
    limit = now() - timedelta(days=2)
    UserUpload.objects.filter(created__lt=limit).delete()
