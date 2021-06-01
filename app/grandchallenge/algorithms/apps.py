from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_algorithm_creators_group(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.algorithms.models import Algorithm

    g, _ = Group.objects.get_or_create(
        name=settings.ALGORITHMS_CREATORS_GROUP_NAME
    )
    assign_perm(
        f"{Algorithm._meta.app_label}.add_{Algorithm._meta.model_name}", g
    )


def init_job_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.algorithms.models import Job

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(f"{Job._meta.app_label}.add_{Job._meta.model_name}", g)


class AlgorithmsConfig(AppConfig):
    name = "grandchallenge.algorithms"

    def ready(self):
        post_migrate.connect(init_algorithm_creators_group, sender=self)
        post_migrate.connect(init_job_permissions, sender=self)
        # noinspection PyUnresolvedReferences
        import grandchallenge.algorithms.signals  # noqa: F401
