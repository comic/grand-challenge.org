from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Job
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=Job.inputs.through)
@receiver(m2m_changed, sender=Job.outputs.through)
def update_view_image_permissions_on_job_io_change(  # noqa:C901
    sender, instance, action, reverse, model, pk_set, **_
):
    """
    Assign or remove view_image permissions for the algorithms editors and
    creators when inputs/outputs are added/removed to/from the algorithm jobs.
    Handles reverse relations and clearing.
    """
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if sender._meta.label_lower == "algorithms.job_inputs":
        reverse_lookup = "algorithms_jobs_as_input"
    elif sender._meta.label_lower == "algorithms.job_outputs":
        reverse_lookup = "algorithms_jobs_as_output"
    else:
        raise RuntimeError("m2m is only valid for Job inputs and outputs.")

    if reverse:
        images = Image.objects.filter(componentinterfacevalue__pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            jobs = getattr(instance, reverse_lookup).all()
        else:
            jobs = model.objects.filter(pk__in=pk_set)

        jobs = jobs.prefetch_related("viewer_groups").only("viewer_groups")
    else:
        jobs = [instance]

        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = Image.objects.filter(
                **{f"componentinterfacevalue__{reverse_lookup}__in": jobs}
            )
        else:
            images = Image.objects.filter(
                componentinterfacevalue__pk__in=pk_set
            )

    images = images.distinct()

    if action == "post_add":
        for job in jobs:
            for group in job.viewer_groups.all():
                assign_perm("view_image", group, images)

    elif action in {"post_remove", "pre_clear"}:
        exclude_jobs = jobs if action == "pre_clear" else None

        for image in images:
            # We cannot remove image permissions directly as the groups
            # may have permissions through another object
            image.update_viewer_groups_permissions(exclude_jobs=exclude_jobs)

    else:
        raise NotImplementedError


def _get_images_for_jobs(*, jobs):
    input_images = Image.objects.filter(
        componentinterfacevalue__algorithms_jobs_as_input__in=jobs
    )
    output_images = Image.objects.filter(
        componentinterfacevalue__algorithms_jobs_as_output__in=jobs
    )
    return input_images.union(output_images)


@receiver(m2m_changed, sender=Job.viewer_groups.through)
def update_view_image_permissions_on_viewer_groups_change(  # noqa:C901
    *_, instance, action, reverse, model, pk_set, **__
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        groups = [instance]
        if pk_set is None:
            jobs = instance.job_set.all()
        else:
            jobs = model.objects.filter(pk__in=pk_set)
    else:
        jobs = [instance]
        if pk_set is None:
            groups = instance.viewer_groups.all()
        else:
            groups = model.objects.filter(pk__in=pk_set)

    images = _get_images_for_jobs(jobs=jobs)

    if action == "post_add":
        for group in groups:
            assign_perm("view_job", group, jobs)
            assign_perm("view_image", group, images)

    elif action in {"post_remove", "pre_clear"}:
        for group in groups:
            for job in jobs:
                remove_perm("view_job", group, job)

        exclude_jobs = jobs if action == "pre_clear" else None

        for image in images:
            # We cannot remove image permissions directly as the groups
            # may have permissions through another object
            image.update_viewer_groups_permissions(exclude_jobs=exclude_jobs)

    else:
        raise NotImplementedError


@receiver(pre_delete, sender=Job)
def update_view_image_permissions_on_job_deletion(*_, instance: Job, **__):
    jobs = [instance]

    for image in _get_images_for_jobs(jobs=jobs):
        # We cannot remove image permissions directly as the groups
        # may have permissions through another object
        image.update_viewer_groups_permissions(exclude_jobs=jobs)
