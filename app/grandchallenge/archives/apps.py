from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_archiveitem_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm("archives.change_archiveitem", g)
    assign_perm("archives.add_archiveitem", g)


class ArchivesConfig(AppConfig):
    name = "grandchallenge.archives"

    def ready(self):
        post_migrate.connect(init_archiveitem_permissions, sender=self)
        # noinspection PyUnresolvedReferences
        import grandchallenge.archives.signals  # noqa: F401
