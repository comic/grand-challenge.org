from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_dicom_creators_group(*_, **__):
    from django.contrib.auth.models import Group

    Group.objects.get_or_create(name=settings.DICOM_DATA_CREATORS_GROUP_NAME)


def init_cases_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.cases.models import RawImageFile, RawImageUploadSession

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{RawImageFile._meta.app_label}.add_{RawImageFile._meta.model_name}",
        g,
    )
    assign_perm(
        f"{RawImageUploadSession._meta.app_label}.add_{RawImageUploadSession._meta.model_name}",
        g,
    )
    assign_perm(
        f"{RawImageUploadSession._meta.app_label}.change_{RawImageUploadSession._meta.model_name}",
        g,
    )


class CasesConfig(AppConfig):
    name = "grandchallenge.cases"

    def ready(self):
        post_migrate.connect(init_dicom_creators_group, sender=self)
        post_migrate.connect(init_cases_permissions, sender=self)
