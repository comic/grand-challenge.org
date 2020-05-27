from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "grandchallenge.components"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.components.signals  # noqa: F401
