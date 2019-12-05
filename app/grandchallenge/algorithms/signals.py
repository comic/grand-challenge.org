from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.emails import (
    send_permission_denied_email,
    send_permission_granted_email,
    send_permission_request_email,
)
from grandchallenge.algorithms.models import AlgorithmPermissionRequest, Result
from grandchallenge.cases.models import Image


@receiver(m2m_changed, sender=Result.images.through)
def update_image_permissions(instance, action, reverse, model, pk_set, **_):
    """
    Assign or remove view permissions to the algorithms editors when images
    are added or remove to/from the algorithm results. Handles reverse
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
            algorithm_results = instance.algorithm_results.all()
        else:
            algorithm_results = model.objects.filter(pk__in=pk_set)

        algorithm_results = algorithm_results.select_related(
            "job__creator", "job__algorithm_image__algorithm__editors_group"
        )
    else:
        algorithm_results = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            images = instance.images.all()
        else:
            images = model.objects.filter(pk__in=pk_set)

    op = assign_perm if "add" in action else remove_perm

    for alg_result in algorithm_results:
        op(
            "view_image",
            alg_result.job.algorithm_image.algorithm.editors_group,
            images,
        )
        op("view_image", alg_result.job.creator, images)


@receiver(pre_save, sender=AlgorithmPermissionRequest)
def process_algorithm_permission_request(sender, instance, *_, **__):
    old_values = sender.objects.filter(pk=instance.pk).first()
    old_status = old_values.status if old_values else None
    if instance.status != old_status:
        if instance.status == AlgorithmPermissionRequest.PENDING:
            send_permission_request_email(instance)
        elif instance.status == AlgorithmPermissionRequest.ACCEPTED:
            instance.algorithm.add_user(instance.user)
            send_permission_granted_email(instance)
        else:
            instance.algorithm.remove_user(instance.user)
            send_permission_denied_email(instance)
