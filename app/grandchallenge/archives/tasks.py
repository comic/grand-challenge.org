from celery import shared_task

from grandchallenge.cases.models import RawImageUploadSession


@shared_task
def add_images_to_archive(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    session.archive.images.add(*session.image_set.all())
