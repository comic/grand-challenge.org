from django.apps import AppConfig


class TeamsConfig(AppConfig):
    name = 'teams'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import teams.signals
