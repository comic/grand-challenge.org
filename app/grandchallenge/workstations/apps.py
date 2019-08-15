from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_workstation_creators_group(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.workstations.models import Workstation

    g, _ = Group.objects.get_or_create(
        name=settings.WORKSTATIONS_CREATORS_GROUP_NAME
    )
    assign_perm(
        f"{Workstation._meta.app_label}.add_{Workstation._meta.model_name}", g
    )


class WorkstationsConfig(AppConfig):
    name = "grandchallenge.workstations"

    def ready(self):
        post_migrate.connect(init_workstation_creators_group, sender=self)
