import os

from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.uploads.models import UploadModel


@receiver(post_save, sender=UploadModel)
def update_uploaded_file_title(instance: UploadModel = None, *_, **__):
    title = os.path.basename(instance.file.name)[0:64]
    UploadModel.objects.filter(pk=instance.pk).update(title=title)
