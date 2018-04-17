# -*- coding: utf-8 -*-
from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.minioupload.models import MinioFile


@receiver(post_save)
def update_parent(instance: MinioFile = None, created: bool = False, *_, **__):
    if not isinstance(instance, MinioFile):
        return

    if created:
        MinioFile.objects.filter(pk=instance.pk).update(
            parent=instance.parent or instance.pk
        )
