# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.core.models import DockerImageModel
from grandchallenge.core.tasks import validate_docker_image_async


@receiver(post_save)
def validate_docker_image(
        instance: DockerImageModel = None, created: bool = False, *_, **__
):
    if isinstance(instance, DockerImageModel) and created:
        validate_docker_image_async.apply_async(
            kwargs={
                'app_label': instance._meta.app_label,
                'object_name': instance._meta.object_name,
                'pk': instance.pk,
            }
        )
