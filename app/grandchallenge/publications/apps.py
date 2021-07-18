from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_publication_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.publications.models import Publication

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{Publication._meta.app_label}.add_{Publication._meta.model_name}", g
    )


class PublicationsConfig(AppConfig):
    name = "grandchallenge.publications"

    def ready(self):
        post_migrate.connect(init_publication_permissions, sender=self)
