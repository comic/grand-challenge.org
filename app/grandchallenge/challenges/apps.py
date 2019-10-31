from django.apps import AppConfig


class ChallengesConfig(AppConfig):
    name = "grandchallenge.challenges"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.challenges.signals  # noqa: F401
