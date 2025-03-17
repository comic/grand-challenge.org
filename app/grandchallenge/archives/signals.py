from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=ArchiveItem.values.through)
def update_permissions_on_archive_item_changed(
    instance, action, reverse, pk_set, **_
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(componentinterfacevalue__pk=instance.pk)
    else:
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = [
                civ.image
                for civ in instance.values.filter(image__isnull=False)
            ]
        else:
            images = Image.objects.filter(
                componentinterfacevalue__pk__in=pk_set
            )

    def update_permissions():
        for image in images:
            image.update_viewer_groups_permissions()

    on_commit(update_permissions)


@receiver(pre_delete, sender=ArchiveItem)
@receiver(post_save, sender=ArchiveItem)
def update_view_image_permissions(*_, instance: ArchiveItem, **__):
    images = [civ.image for civ in instance.values.filter(image__isnull=False)]

    def update_permissions():
        for image in images:
            image.update_viewer_groups_permissions()

    on_commit(update_permissions)
