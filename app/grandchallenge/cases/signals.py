from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.cases.models import (
    RawImageUploadSession, UPLOAD_SESSION_STATE
)
from grandchallenge.cases.tasks import build_images
from grandchallenge.core.utils import disable_for_loaddata


@receiver(post_save, sender=RawImageUploadSession)
@disable_for_loaddata
def queue_build_image_job(
        instance: RawImageUploadSession = None, created: bool = False, *_, **__
):
    if created:
        try:

            RawImageUploadSession.objects.filter(pk=instance.pk).update(
                session_state=UPLOAD_SESSION_STATE.queued,
                processing_task=instance.pk
            )

            build_images.apply_async(
                task_id=str(instance.pk), args=(instance.pk,),
            )

        except Exception as e:
            instance.session_state = UPLOAD_SESSION_STATE.stopped
            instance.error_message = f"Could not start job: {e}"
            instance.save()
            raise e
