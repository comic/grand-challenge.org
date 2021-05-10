from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.archives.models import Archive, ArchiveItem
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


@receiver(m2m_changed, sender=ArchiveItem.values.through)
def on_archive_images_changed(instance, action, reverse, model, pk_set, **_):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            archive_items = model.objects.filter(values=instance)
        else:
            archive_items = model.objects.filter(pk__in=pk_set)

        archive_item_pks = archive_items.values_list("pk", flat=True)
        archive_pks = archive_items.values_list("archive_id", flat=True)
    else:
        archive_pks = [instance.archive_id]
        archive_item_pks = [instance.pk]
    if "add" in action:
        on_commit(
            lambda: create_algorithm_jobs_for_archive.apply_async(
                kwargs={
                    "archive_pks": list(archive_pks),
                    "archive_item_pks": list(archive_item_pks),
                },
            )
        )


@receiver(m2m_changed, sender=Archive.algorithms.through)
def on_archive_algorithms_changed(
    instance, action, reverse, model, pk_set, **_
):
    if action != "post_add":
        # nothing to do for the other actions
        return

    if reverse:
        algorithm_pks = [instance.pk]
        archive_pks = pk_set
    else:
        archive_pks = [instance.pk]
        algorithm_pks = pk_set

    on_commit(
        lambda: create_algorithm_jobs_for_archive.apply_async(
            kwargs={
                "archive_pks": list(archive_pks),
                "algorithm_pks": list(algorithm_pks),
            },
        )
    )
