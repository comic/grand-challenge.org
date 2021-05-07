from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.archives.models import Archive, ArchiveItem
from grandchallenge.cases.models import Image
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
)


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


# @receiver(m2m_changed, sender=Archive.images.through)
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
