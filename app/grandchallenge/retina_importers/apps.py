from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_retina_import_user(*_, **__):
    from django.contrib.auth import get_user_model

    get_user_model().objects.get_or_create(
        username=settings.RETINA_IMPORT_USER_NAME
    )


class RetinaImportersConfig(AppConfig):
    name = "grandchallenge.retina_importers"

    def ready(self):
        post_migrate.connect(init_retina_import_user)
