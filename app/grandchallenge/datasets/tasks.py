from celery import shared_task

from grandchallenge.cases.models import RawImageUploadSession


@shared_task
def add_images_to_annotation_set(*_, upload_session_pk):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)
    session.annotationset.images.add(*session.image_set.all())
