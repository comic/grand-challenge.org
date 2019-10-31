from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def init_reader_study_creators_group(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.reader_studies.models import ReaderStudy

    g, _ = Group.objects.get_or_create(
        name=settings.READER_STUDY_CREATORS_GROUP_NAME
    )
    assign_perm(
        f"{ReaderStudy._meta.app_label}.add_{ReaderStudy._meta.model_name}", g
    )


class ReaderStudiesConfig(AppConfig):
    name = "grandchallenge.reader_studies"

    def ready(self):
        post_migrate.connect(init_reader_study_creators_group, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.reader_studies.signals  # noqa: F401
