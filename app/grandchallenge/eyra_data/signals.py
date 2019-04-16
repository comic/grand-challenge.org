from django.db.models.signals import pre_save
from django.dispatch import receiver

from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.eyra_data.models import DataFile


@receiver(pre_save, sender=DataFile)
@disable_for_loaddata
def set_size(
    instance: DataFile = None, *_, **__
):
    print("Should update size")
