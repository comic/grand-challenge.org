from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_reader_study_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        "reader_studies.change_readerstudy",
        g,
    )
    assign_perm(
        "reader_studies.add_displayset",
        g,
    )
    assign_perm(
        "reader_studies.change_displayset",
        g,
    )
    assign_perm(
        "reader_studies.delete_displayset",
        g,
    )


def init_answer_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm

    from grandchallenge.reader_studies.models import Answer

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(f"{Answer._meta.app_label}.add_{Answer._meta.model_name}", g)
    assign_perm(
        f"{Answer._meta.app_label}.change_{Answer._meta.model_name}", g
    )


class ReaderStudiesConfig(AppConfig):
    name = "grandchallenge.reader_studies"

    def ready(self):
        post_migrate.connect(init_reader_study_permissions, sender=self)
        post_migrate.connect(init_answer_permissions, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.reader_studies.signals  # noqa: F401
