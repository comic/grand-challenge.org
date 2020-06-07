from celery import shared_task
from django.db.models import F

from grandchallenge.serving.models import Download


@shared_task
def create_download(*_, **kwargs):
    d, created = Download.objects.get_or_create(**kwargs)

    if not created:
        d.count = F("count") + 1
        d.save()
