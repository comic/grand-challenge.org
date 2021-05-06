from django.db.models.signals import m2m_changed, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


@receiver(m2m_changed, sender=ArchiveItem.values.through)
def update_permissions_on_archive_item_changed(
    instance, action, reverse, model, pk_set, **_
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
            # TODO: this should be the same as [civ.image for civ in instance.items.all()], double check this
            images = Image.objects.filter(
                componentinterfacevalue__archive_items=instance
            )
        else:
            images = Image.objects.filter(
                componentinterfacevalue__pk__in=pk_set
            )

    op = assign_perm if "add" in action else remove_perm

    for archive_item in archive_items:
        op("view_image", archive_item.archive.editors_group, images)
        op("view_image", archive_item.archive.uploaders_group, images)
        op("view_image", archive_item.archive.users_group, images)


@receiver(pre_delete, sender=ArchiveItem)
def remove_view_image_permissions(*_, instance: ArchiveItem, **__):
    """
    Remove view_images perm when the archive item is deleted

    Note that this will remove permissions regardless of whether
    the image is included in an archive via another archive item.
    """
    # TODO: this should be the same as [civ.image for civ in instance.items.all()], double check this
    images = Image.objects.filter(
        componentinterfacevalue__archive_items=instance
    )

    remove_perm("view_image", instance.archive.editors_group, images)
    remove_perm("view_image", instance.archive.uploaders_group, images)
    remove_perm("view_image", instance.archive.users_group, images)


@receiver(m2m_changed, sender=Archive.images.through)
def on_archive_images_changed(instance, action, reverse, model, pk_set, **_):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            archives = instance.archive_set.all()
        else:
            archives = model.objects.filter(pk__in=pk_set)

        archive_pks = archives.values_list("pk", flat=True)
    else:
        archive_pks = [instance.pk]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = instance.images.all()
        else:
            images = model.objects.filter(pk__in=pk_set)

    # TODO: This is a temporary workaround. The images field on Archives should
    # not be used anymore. Instead, ArchiveItems should be directly created.
    # The civs sent to the task should then be grouped by AchiveItem.
    interface = ComponentInterface.objects.get(slug="generic-medical-image")
    civs = []
    for image in images:
        for archive in image.archive_set.all():
            civ, _ = ComponentInterfaceValue.objects.get_or_create(
                interface=interface, image=image
            )
            civs.append(civ.pk)
            if not ArchiveItem.objects.filter(
                archive=archive, values__in=[civ.pk]
            ).exists():
                item = ArchiveItem.objects.create(archive=archive)
                item.values.set([civ])

    if "add" in action:
        on_commit(
            lambda: create_algorithm_jobs_for_archive.apply_async(
                kwargs={"archive_pks": list(archive_pks), "civ_pks": civs},
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
