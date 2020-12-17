from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.reader_studies.models import ReaderStudy


@receiver(m2m_changed, sender=Algorithm.organizations.through)
@receiver(m2m_changed, sender=Archive.organizations.through)
@receiver(m2m_changed, sender=Challenge.organizations.through)
@receiver(m2m_changed, sender=ExternalChallenge.organizations.through)
@receiver(m2m_changed, sender=ReaderStudy.organizations.through)
def update_related_permissions(
    sender, instance, action, reverse, model, pk_set, **_
):
    if action not in ["post_add", "post_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if sender == Algorithm.organizations.through:
        related_model = Algorithm
        related_name = "algorithms"
    elif sender == Archive.organizations.through:
        related_model = Archive
        related_name = "archives"
    elif sender == Challenge.organizations.through:
        related_model = Challenge
        related_name = "challenges"
    elif sender == ExternalChallenge.organizations.through:
        related_model = ExternalChallenge
        related_name = "externalchallenges"
    elif sender == ReaderStudy.organizations.through:
        related_model = ReaderStudy
        related_name = "readerstudies"
    else:
        raise RuntimeError(f"Unrecognised sender: {sender}")

    _update_related_view_permissions(
        action=action,
        instance=instance,
        model=model,
        pk_set=pk_set,
        reverse=reverse,
        related_model=related_model,
        related_name=related_name,
    )


def _update_related_view_permissions(
    *, action, instance, model, pk_set, reverse, related_model, related_name,
):
    if reverse:
        organizations = [instance]
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            related_objects = getattr(instance, related_name).all()
        else:
            related_objects = model.objects.filter(pk__in=pk_set)
    else:
        related_objects = related_model.objects.filter(pk=instance.pk)
        if pk_set is None:
            # When using a _clear action, pk_set is None
            # https://docs.djangoproject.com/en/2.2/ref/signals/#m2m-changed
            organizations = instance.organizations.all()
        else:
            organizations = model.objects.filter(pk__in=pk_set)

    op = assign_perm if "add" in action else remove_perm
    perm = f"view_{related_model._meta.model_name}"

    for org in organizations:
        op(
            perm, org.editors_group, related_objects,
        )
        op(
            perm, org.members_group, related_objects,
        )
