from celery import shared_task
from django.db.models import F

from grandchallenge.serving.models import Download


@shared_task
def create_download(*, creator_id, image_id):
    kwargs = {"creator_id": creator_id, "image_id": image_id}

    n_updated = Download.objects.filter(**kwargs).update(count=F("count") + 1)

    if n_updated == 0:
        Download.objects.create(**kwargs)
