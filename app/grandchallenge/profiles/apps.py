from django.apps import AppConfig


class MyAppConfig(AppConfig):
    name = "grandchallenge.profiles"

    def ready(self):
        import grandchallenge.profiles.signals  # noqa: F401
