from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.reader_studies.models import ReaderStudy


@receiver(m2m_changed, sender=ReaderStudy.images.through)
def update_image_permissions(instance, action, reverse, model, pk_set, **_):
    """
    Assign or remove view permissions to the readers group when images
    are added or remove to/from the reader study images. Handles reverse
    relations and clearing.
    """
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    op = assign_perm if "add" in action else remove_perm

    if reverse:
        images = [instance]
        try:
            reader_studies = model.objects.filter(pk__in=pk_set)
        except TypeError:
            # When a clear method is used pk_set is none and a TypeError raised
            reader_studies = images[0].readerstudies.all()
    else:
        reader_studies = [instance]
        try:
            images = model.objects.filter(pk__in=pk_set)
        except TypeError:
            # When a clear method is used pk_set is none and a TypeError raised
            images = reader_studies[0].images.all()

    for im in images:
        for rs in reader_studies:
            op("view_image", rs.readers_group, im)
