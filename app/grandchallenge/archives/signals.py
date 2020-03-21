from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.archives.models import Archive
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=Archive.images.through)
def update_image_permissions(instance, action, reverse, model, pk_set, **_):
    """
    Assign or remove view permissions to the archive groups when images
    are added or remove to/from the archive images. Handles reverse
    relations and clearing.
    """
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            archives = instance.archives.all()
        else:
            archives = model.objects.filter(pk__in=pk_set)

        archives = archives.select_related("users_group", "editors_group")
    else:
        archives = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = instance.images.all()
        else:
            images = model.objects.filter(pk__in=pk_set)

    op = assign_perm if "add" in action else remove_perm

    for archive in archives:
        op("view_image", archive.users_group, images)
        op("view_image", archive.editors_group, images)
