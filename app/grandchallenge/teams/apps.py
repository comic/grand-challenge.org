from django.apps import AppConfig


class TeamsConfig(AppConfig):
    name = "grandchallenge.teams"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.teams.signals  # noqa: F401
