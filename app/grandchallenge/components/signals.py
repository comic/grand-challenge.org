from django.db.models.signals import pre_delete
from django.dispatch import receiver

from grandchallenge.components.models import ComponentImage, Tarball


@receiver(pre_delete)
def delete_linked_file(instance, **_):
    if isinstance(instance, (ComponentImage, Tarball)):
        instance.linked_file.delete(save=False)
