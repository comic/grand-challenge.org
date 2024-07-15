from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db.models.signals import post_migrate

from grandchallenge.core.fixtures import create_uploaded_image


def init_default_workstation(*_, **__):
    from grandchallenge.workstations.models import Workstation

    try:
        Workstation.objects.get(slug=settings.DEFAULT_WORKSTATION_SLUG)
    except ObjectDoesNotExist:
        # get_or_create with defaults does not work here due to slug setting
        w = Workstation.objects.create(
            title=settings.DEFAULT_WORKSTATION_SLUG,
            logo=create_uploaded_image(),
            public=True,
        )

        if w.slug != settings.DEFAULT_WORKSTATION_SLUG:
            raise ImproperlyConfigured(
                f"DEFAULT_WORKSTATION_SLUG is not a valid slug, use {w.slug}"
            )


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


def init_session_and_feedback_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    from grandchallenge.workstations.models import Feedback, Session

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{Session._meta.app_label}.change_{Session._meta.model_name}", g
    )
    assign_perm(
        f"{Feedback._meta.app_label}.add_{Feedback._meta.model_name}", g
    )


class WorkstationsConfig(AppConfig):
    name = "grandchallenge.workstations"

    def ready(self):
        from grandchallenge.workstations import signals  # noqa F401

        post_migrate.connect(init_default_workstation, sender=self)
        post_migrate.connect(init_workstation_creators_group, sender=self)
        post_migrate.connect(
            init_session_and_feedback_permissions, sender=self
        )
