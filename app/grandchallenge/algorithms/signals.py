from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Job
from grandchallenge.components.models import ComponentInterfaceValue


@receiver(m2m_changed, sender=Job.inputs.through)
@receiver(m2m_changed, sender=Job.outputs.through)
def update_input_image_permissions(
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
        forward_lookup = "inputs"
        reverse_lookup = "algorithms_jobs_as_input"
    elif sender._meta.label_lower == "algorithms.job_outputs":
        forward_lookup = "outputs"
        reverse_lookup = "algorithms_jobs_as_output"
    else:
        raise RuntimeError("m2m is only valid for Job inputs and outputs.")

    if reverse:
        component_interface_values = ComponentInterfaceValue.objects.filter(
            pk=instance.pk, image__isnull=False
        )
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            jobs = getattr(instance, reverse_lookup).all()
        else:
            jobs = model.objects.filter(pk__in=pk_set)
    else:
        jobs = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            component_interface_values = getattr(
                instance, forward_lookup
            ).filter(image__isnull=False)
        else:
            component_interface_values = model.objects.filter(
                pk__in=pk_set, image__isnull=False
            )

    _update_image_permissions(
        jobs=jobs,
        component_interface_values=component_interface_values,
        exclude_jobs=action == "pre_clear",
    )


def _get_image_civs(*, jobs):
    queryset = ComponentInterfaceValue.objects.filter(
        image__isnull=False
    ).select_related("image")

    input_civs = queryset.filter(algorithms_jobs_as_input__in=jobs)
    output_civs = queryset.filter(algorithms_jobs_as_output__in=jobs)

    return {*input_civs, *output_civs}


def _update_image_permissions(
    *, jobs, component_interface_values, exclude_jobs: bool
):
    for civ in component_interface_values:
        # image__isnull=False is used above so we know that civ.image exists
        civ.image.update_viewer_groups_permissions(
            exclude_jobs=jobs if exclude_jobs else None
        )


@receiver(m2m_changed, sender=Job.viewer_groups.through)
def update_group_permissions(
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

    operation = assign_perm if "add" in action else remove_perm

    for job in jobs:
        for group in groups:
            operation("view_job", group, job)

    component_interface_values = _get_image_civs(jobs=jobs)

    _update_image_permissions(
        jobs=jobs,
        component_interface_values=component_interface_values,
        exclude_jobs=action == "pre_clear",
    )


@receiver(pre_delete, sender=Job)
def update_permissions_on_job_deletion(*_, instance: Job, signal, **__):
    jobs = [instance]

    component_interface_values = _get_image_civs(jobs=jobs)

    _update_image_permissions(
        jobs=jobs,
        component_interface_values=component_interface_values,
        exclude_jobs=signal == pre_delete,
    )
