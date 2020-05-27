from celery import shared_task
from django.db.models import F

from grandchallenge.serving.models import Download


@shared_task
def create_download(*_, **kwargs):
    try:
        d = Download.objects.get(**kwargs)
        d.count = F("count") + 1
        d.save()
    except Download.DoesNotExist:
        Download.objects.create(**kwargs)
