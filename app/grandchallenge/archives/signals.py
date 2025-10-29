from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.db.transaction import on_commit
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=ArchiveItem.values.through)
def update_permissions_on_archive_item_changed(
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

        archive_items = archive_items.select_related(
            "archive__editors_group",
            "archive__uploaders_group",
            "archive__users_group",
        ).only(
            "archive__editors_group",
            "archive__uploaders_group",
            "archive__users_group",
        )
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

    if action == "post_add":
        for archive_item in archive_items:
            for image in images:
                groups = [
                    archive_item.archive.editors_group,
                    archive_item.archive.uploaders_group,
                    archive_item.archive.users_group,
                ]
                assign_perm("view_image", groups, image)

    elif action in {"post_remove", "pre_clear"}:
        for image in images:
            image.update_viewer_groups_permissions(
                exclude_archive_items=archive_items
            )
    else:
        raise NotImplementedError


@receiver(pre_delete, sender=ArchiveItem)
@receiver(post_save, sender=ArchiveItem)
def update_view_image_permissions(*_, instance: ArchiveItem, **__):
    images = [civ.image for civ in instance.values.filter(image__isnull=False)]

    def update_permissions():
        for image in images:
            image.update_viewer_groups_permissions()

    on_commit(update_permissions)
