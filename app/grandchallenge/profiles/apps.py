from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_profile_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.profiles.models import UserProfile

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{UserProfile._meta.app_label}.change_{UserProfile._meta.model_name}",
        g,
    )


class ProfilesConfig(AppConfig):
    name = "grandchallenge.profiles"

    def ready(self):
        post_migrate.connect(init_profile_permissions, sender=self)
