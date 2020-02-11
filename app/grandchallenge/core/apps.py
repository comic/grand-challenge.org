from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_users_groups(*_, **__):
    from django.contrib.auth.models import Group

    for g in [
        settings.REGISTERED_AND_ANON_USERS_GROUP_NAME,
        settings.REGISTERED_USERS_GROUP_NAME,
    ]:
        _ = Group.objects.get_or_create(name=g)


class CoreConfig(AppConfig):
    name = "grandchallenge.core"

    def ready(self):
        post_migrate.connect(init_users_groups, sender=self)
