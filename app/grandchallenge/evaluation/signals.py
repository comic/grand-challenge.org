from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import m2m_changed, pre_delete
from django.dispatch import receiver

from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    CombinedLeaderboardPhase,
    Phase,
)


@receiver(pre_delete, sender=Phase)
def clean_up_submission_follows(instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()


@receiver(m2m_changed, sender=CombinedLeaderboardPhase)
def handle_combined_leaderboard_phase_change(
    sender, instance, action, reverse, **_
):
    if action not in ["post_add", "pre_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        leaderboards = CombinedLeaderboard.objects.filter(
            phases__pk=instance.pk
        )
    else:
        leaderboards = [instance]

    for leaderboard in leaderboards:
        leaderboard.schedule_combined_ranks_update()
