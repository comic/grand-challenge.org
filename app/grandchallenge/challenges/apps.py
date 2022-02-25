from django.apps import AppConfig
from django.db.models.signals import post_migrate

from config import settings


def init_challenge_request_reviewer_group(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    g, _ = Group.objects.get_or_create(
        name=settings.CHALLENGE_REVIEWERS_GROUP_NAME
    )
    assign_perm("challenges.change_challengerequest", g)
    assign_perm("challenges.view_challengerequest", g)


class ChallengesConfig(AppConfig):
    name = "grandchallenge.challenges"

    def ready(self):
        post_migrate.connect(
            init_challenge_request_reviewer_group, sender=self
        )
