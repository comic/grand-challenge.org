from django.apps import AppConfig


class ChallengesConfig(AppConfig):
    name = 'challenges'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import challenges.signals
