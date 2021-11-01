from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_retina_groups(*_, **__):
    from django.contrib.auth.models import Group

    Group.objects.get_or_create(name=settings.RETINA_ADMINS_GROUP_NAME)
    Group.objects.get_or_create(name=settings.RETINA_GRADERS_GROUP_NAME)


class RetinaAPIConfig(AppConfig):
    name = "grandchallenge.retina_api"

    def ready(self):
        post_migrate.connect(init_retina_groups)
