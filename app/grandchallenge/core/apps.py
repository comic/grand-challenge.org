from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_all_users_group(*_, **__):
    from django.contrib.auth.models import Group

    _ = Group.objects.get_or_create(name=settings.ALL_USERS_GROUP_NAME)


class CoreConfig(AppConfig):
    name = "grandchallenge.core"

    def ready(self):
        post_migrate.connect(init_all_users_group, sender=self)
