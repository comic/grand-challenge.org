from django.db.models.signals import m2m_changed
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

        jobs = jobs.select_related(
            "creator", "algorithm_image__algorithm__editors_group"
        )
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
        operation=assign_perm if "add" in action else remove_perm,
        exclude_jobs=action == "pre_clear",
    )


def _update_image_permissions(
    *, jobs, component_interface_values, operation, exclude_jobs: bool,
):
    for civ in component_interface_values:
        # image__isnull=False is used above so we know that civ.image exists
        for job in jobs:
            operation(
                "view_image",
                job.algorithm_image.algorithm.editors_group,
                civ.image,
            )
            if job.creator is not None:
                operation("view_image", job.creator, civ.image)

        civ.image.update_public_group_permissions(
            exclude_jobs=jobs if exclude_jobs else None,
        )
