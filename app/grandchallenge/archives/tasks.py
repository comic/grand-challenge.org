from celery import shared_task

from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image


@shared_task
def add_images_to_archive(*, upload_session_pk, archive_pk):
    images = Image.objects.filter(origin_id=upload_session_pk)
    archive = Archive.objects.get(pk=archive_pk)

    archive.images.add(*images.all())
