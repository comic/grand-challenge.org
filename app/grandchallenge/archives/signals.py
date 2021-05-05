from django.db.models.signals import m2m_changed
from django.db.transaction import on_commit
from django.dispatch import receiver

from grandchallenge.algorithms.tasks import create_algorithm_jobs_for_archive
from grandchallenge.archives.models import Archive


@receiver(m2m_changed, sender=Archive.algorithms.through)
def on_archive_algorithms_changed(
    instance, action, reverse, model, pk_set, **_
):
    if action != "post_add":
        # nothing to do for the other actions
        return

    if reverse:
        algorithm_pks = [instance.pk]
        archive_pks = pk_set
    else:
        archive_pks = [instance.pk]
        algorithm_pks = pk_set

    on_commit(
        lambda: create_algorithm_jobs_for_archive.apply_async(
            kwargs={
                "archive_pks": list(archive_pks),
                "algorithm_pks": list(algorithm_pks),
            },
        )
    )
