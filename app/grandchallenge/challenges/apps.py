from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_reviewers_group(sender, **kwargs):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    from grandchallenge.challenges.models import ChallengeRequest

    g, _ = Group.objects.get_or_create(
        name=settings.CHALLENGES_REVIEWERS_GROUP_NAME
    )
    assign_perm(
        f"{ChallengeRequest._meta.app_label}.view_{ChallengeRequest._meta.model_name}",
        g,
    )
    assign_perm(
        f"{ChallengeRequest._meta.app_label}.change_{ChallengeRequest._meta.model_name}",
        g,
    )


class ChallengesConfig(AppConfig):
    name = "grandchallenge.challenges"

    def ready(self):
        post_migrate.connect(init_reviewers_group, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.challenges.signals  # noqa: F401
