from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from grandchallenge.evaluation.models import (
    CombinedLeaderboard,
    CombinedLeaderboardPhase,
)


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
