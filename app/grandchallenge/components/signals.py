from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.components.models import ComponentImage, ComponentJob
from grandchallenge.components.tasks import (
    validate_docker_image as validate_docker_image_async,
)
from grandchallenge.core.utils import disable_for_loaddata


@receiver(post_save)
@disable_for_loaddata
def validate_docker_image(
    instance: ComponentImage = None, created: bool = False, *_, **__
):
    if isinstance(instance, ComponentImage) and created:
        validate_docker_image_async.apply_async(
            kwargs={
                "app_label": instance._meta.app_label,
                "model_name": instance._meta.model_name,
                "pk": instance.pk,
            }
        )


@receiver(post_save)
@disable_for_loaddata
def schedule_job(
    instance: ComponentJob = None, created: bool = False, *_, **__
):
    if isinstance(instance, ComponentJob) and created:
        return instance.schedule_job()
