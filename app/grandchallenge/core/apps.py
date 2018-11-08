from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "grandchallenge.core"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.core.signals
