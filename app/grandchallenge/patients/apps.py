from django.apps import AppConfig


class Config(AppConfig):
    name = "grandchallenge.patients"

    def ready(self):
        try:
            import users.signals  # noqa F401
        except ImportError:
            pass
