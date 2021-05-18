from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_reader_study_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.reader_studies.models import ReaderStudy

    g, _ = Group.objects.get_or_create(
        name=settings.READER_STUDY_CREATORS_GROUP_NAME
    )
    assign_perm(
        f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}", g
    )

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{ReaderStudy._meta.app_label}.change_{ReaderStudy._meta.model_name}",
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
