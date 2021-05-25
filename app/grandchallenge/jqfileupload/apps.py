from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_jqfileupload_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.jqfileupload.models import StagedFile

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{StagedFile._meta.app_label}.add_{StagedFile._meta.model_name}", g,
    )


class JQFileUploadConfig(AppConfig):
    name = "grandchallenge.jqfileupload"

    def ready(self):
        post_migrate.connect(init_jqfileupload_permissions, sender=self)
