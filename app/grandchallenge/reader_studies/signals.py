from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import Answer, ReaderStudy
from grandchallenge.reader_studies.tasks import add_scores


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

    if reverse:
        images = Image.objects.filter(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            reader_studies = instance.readerstudies.all()
        else:
            reader_studies = model.objects.filter(pk__in=pk_set)

        reader_studies = reader_studies.select_related("readers_group")
    else:
        reader_studies = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = instance.images.all()
        else:
            images = model.objects.filter(pk__in=pk_set)

    op = assign_perm if "add" in action else remove_perm

    for rs in reader_studies:
        op("view_image", rs.readers_group, images)


@receiver(m2m_changed, sender=Answer.images.through)
def assign_score(instance, action, reverse, model, pk_set, **_):
    if action != "post_add":
        return
    add_scores.apply_async(
        kwargs={
            "instance_pk": str(instance.pk),
            "pk_set": list(map(str, pk_set)),
        }
    )
