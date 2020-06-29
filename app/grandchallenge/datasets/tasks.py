from celery import shared_task

from grandchallenge.cases.models import RawImageUploadSession


@shared_task
def add_images_to_annotationset(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    session.annotationset.images.add(*session.image_set.all())


@shared_task
def add_images_to_imageset(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    session.imageset.images.add(*session.image_set.all())
