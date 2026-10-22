from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from grandchallenge.cases.models import Image
from grandchallenge.evaluation.models import BatchJobTask


@receiver(m2m_changed, sender=BatchJobTask.outputs.through)
def update_view_image_permissions_on_batch_job_task_output_change(
    instance, action, reverse, model, pk_set, **_
):
    """
    Assign or remove view_image permissions for the challenge admins
    when inputs/outputs are added/removed to/from the algorithm jobs.
    Handles reverse relations and clearing.
    """
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        images = Image.objects.filter(componentinterfacevalue__pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/stable/ref/signals/#m2m-changed
            tasks = instance.evaluation_batchjobtasks_as_output.all()
        else:
            tasks = model.objects.filter(pk__in=pk_set)
    else:
        tasks = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            images = Image.objects.filter(
                componentinterfacevalue__evaluation_batchjobtasks_as_output__in=tasks
            )
        else:
            images = Image.objects.filter(
                componentinterfacevalue__pk__in=pk_set
            )

    images = images.distinct()

    if action == "post_add":
        admins_groups = {
            task.batch_job.submission.phase.challenge.admins_group
            for task in tasks
        }
        for admins_group in admins_groups:
            assign_perm("view_image", admins_group, images)

    elif action in {"post_remove", "pre_clear"}:
        exclude_batch_job_tasks = tasks if action == "pre_clear" else None
        for image in images:
            # We cannot remove image permissions directly as the challenge
            # admins may have view_image through another object.
            image.update_viewer_groups_permissions(
                exclude_batch_job_tasks=exclude_batch_job_tasks
            )

    else:
        raise NotImplementedError
