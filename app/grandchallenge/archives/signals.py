from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=ArchiveItem.values.through)
def update_view_image_permissions_on_archive_item_values_change(
    *, instance, action, reverse, model, pk_set, **_
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(componentinterfacevalue__pk=instance.pk)

        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            archive_items = instance.archive_items.all()
        else:
            archive_items = model.objects.filter(pk__in=pk_set)

    else:
        archive_items = [instance]

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

    exclude_archive_items = archive_items if action == "pre_clear" else None

    for image in images:
        image.update_viewer_groups_permissions(
            exclude_archive_items=exclude_archive_items
        )


@receiver(pre_delete, sender=ArchiveItem)
@receiver(post_save, sender=ArchiveItem)
def update_view_image_permissions_on_archive_item_change(
    *, instance: ArchiveItem, signal, **__
):
    images = Image.objects.filter(
        componentinterfacevalue__archive_items=instance
    ).distinct()
    exclude_archive_items = [instance] if signal is pre_delete else None

    for image in images:
        image.update_viewer_groups_permissions(
            exclude_archive_items=exclude_archive_items
        )
