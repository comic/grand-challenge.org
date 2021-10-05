from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_upload_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.uploads.models import UserUpload, UserUploadFile

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{UserUpload._meta.app_label}.add_{UserUpload._meta.model_name}", g,
    )
    assign_perm(
        f"{UserUploadFile._meta.app_label}.add_{UserUploadFile._meta.model_name}",
        g,
    )
    assign_perm(
        f"{UserUploadFile._meta.app_label}.change_{UserUploadFile._meta.model_name}",
        g,
    )


class UploadsConfig(AppConfig):
    name = "grandchallenge.uploads"

    def ready(self):
        post_migrate.connect(init_upload_permissions, sender=self)
