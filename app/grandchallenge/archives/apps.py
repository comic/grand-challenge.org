from django.apps import AppConfig


class ArchivesConfig(AppConfig):
    name = "grandchallenge.archives"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.archives.signals  # noqa: F401
