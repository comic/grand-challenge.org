from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.cases.models import RawImageUploadSession, \
    UPLOAD_SESSION_STATE
from grandchallenge.cases.tasks import build_images_task

PREVENT_JOB_CREATION_ON_SAVE = False


@receiver(post_save, sender=RawImageUploadSession)
def execute_job(
        instance: RawImageUploadSession=None, created: bool=False,
        *_, **__):
    if created and not PREVENT_JOB_CREATION_ON_SAVE:
        instance.session_state = UPLOAD_SESSION_STATE.queued
        instance.save()

        try:
            build_images_task.apply_async(
                args=(instance.pk, ),
            )
        except Exception as e:
            instance.session_state = UPLOAD_SESSION_STATE.stopped
            instance.error_message = f"Could not start job: {e}"
            instance.save()
            raise e
