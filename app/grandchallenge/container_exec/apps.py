from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "grandchallenge.container_exec"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.container_exec.signals  # noqa: F401
