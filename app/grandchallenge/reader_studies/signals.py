from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save
from django.db.transaction import on_commit
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.cases.models import Image
from grandchallenge.reader_studies.models import (
    Answer,
    DisplaySet,
    ReaderStudy,
)
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

        reader_studies = reader_studies.select_related(
            "readers_group", "editors_group"
        )
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
        op("view_image", rs.editors_group, images)
        op("view_image", rs.readers_group, images)


@receiver(m2m_changed, sender=Answer.images.through)
def assign_score(instance, action, reverse, model, pk_set, **_):
    if action != "post_add":
        return

    on_commit(
        lambda: add_scores.apply_async(
            kwargs={
                "instance_pk": str(instance.pk),
                "pk_set": list(map(str, pk_set)),
            }
        )
    )


@receiver(m2m_changed, sender=DisplaySet.values.through)
def assert_modification_allowed(instance, action, reverse, model, pk_set, **_):
    if "pre" not in action:
        return

    if reverse:
        not_editable = DisplaySet.objects.filter(
            answers__isnull=False
        ).values_list("pk", flat=True)
        if len(not_editable) > 0:
            raise ValidationError(
                "The following display sets cannot be updated, because answers "
                f"for them already exist: {', '.join(map(str, not_editable))}"
            )

    else:
        if not instance.is_editable:
            raise ValidationError(
                "This display set cannot be updated, because answers for it "
                "already exist."
            )


@receiver(m2m_changed, sender=DisplaySet.values.through)
def update_reader_study_modification_time(
    instance, action, reverse, model, pk_set, **_
):
    """Call save on corresponding reader study to update modified field."""
    if "post" not in action:
        return

    if reverse:
        for ds in DisplaySet.objects.filter(pk__in=pk_set):
            with transaction.atomic():
                ds.reader_study.save()

    else:
        with transaction.atomic():
            instance.reader_study.save()


@receiver(post_save, sender=DisplaySet)
def set_display_set_order(sender, instance, created, **_):
    """Set to first multiple of 10 that is higher than the highest in this rs."""
    if not created:
        return

    last = instance.reader_study.display_sets.last()
    highest = getattr(last, "order", 0)
    instance.order = (highest + 10) // 10 * 10
    instance.save()
