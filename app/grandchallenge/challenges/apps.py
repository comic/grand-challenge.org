from django.apps import AppConfig
from django.db.models.signals import post_migrate


def init_challenge_forum_category(*_, **__):
    from machina.apps.forum.models import Forum
    from machina.apps.forum_permission.models import UserForumPermission
    from machina.apps.forum_permission.models import ForumPermission

    from django.conf import settings

    f, _ = Forum.objects.get_or_create(
        name=settings.FORUMS_CHALLENGE_CATEGORY_NAME, type=Forum.FORUM_CAT,
    )

    for codename in ["can_see_forum", "can_read_forum"]:
        perm = ForumPermission.objects.get(codename=codename)
        for user in ["anonymous_user", "authenticated_user"]:
            # All users should be able to see the challenge category
            p, _ = UserForumPermission.objects.get_or_create(
                permission=perm, **{user: True}, forum=f, has_perm=True
            )


class ChallengesConfig(AppConfig):
    name = "grandchallenge.challenges"

    def ready(self):
        post_migrate.connect(init_challenge_forum_category, sender=self)
