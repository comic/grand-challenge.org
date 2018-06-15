from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.cases.models import RawImageUploadSession, \
    UPLOAD_SESSION_STATE
from grandchallenge.cases.tasks import build_images


@receiver(post_save, sender=RawImageUploadSession)
def execute_job(
        instance: RawImageUploadSession=None, created: bool=False,
        *_, **__):
    if created:
        build_images.apply_async(
            args=(instance.pk, ),
        )
        instance.session_state = UPLOAD_SESSION_STATE.queued
        instance.save()
