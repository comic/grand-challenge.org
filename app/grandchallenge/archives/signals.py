from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=Archive.images.through)
def on_archive_images_changed(instance, action, reverse, model, pk_set, **_):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(pk=instance.pk)
        image_pks = [instance.pk]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            archives = instance.archive_set.all()
        else:
            archives = model.objects.filter(pk__in=pk_set)

        archive_pks = archives.values_list("pk", flat=True)
        archives = archives.select_related("users_group", "editors_group")
    else:
        archives = [instance]
        archive_pks = [instance.pk]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = instance.images.all()
        else:
            images = model.objects.filter(pk__in=pk_set)
        image_pks = images.values_list("pk", flat=True)

    op = assign_perm if "add" in action else remove_perm

    for archive in archives:
        op("view_image", archive.editors_group, images)
        op("view_image", archive.uploaders_group, images)
        op("view_image", archive.users_group, images)

    if "add" in action:
        create_algorithm_jobs_for_archive.apply_async(
            kwargs={
                "archive_pks": list(archive_pks),
                "image_pks": list(image_pks),
            },
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

    create_algorithm_jobs_for_archive.apply_async(
        kwargs={
            "archive_pks": list(archive_pks),
            "algorithm_pks": list(algorithm_pks),
        },
    )
