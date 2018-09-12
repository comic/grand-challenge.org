from django.apps import AppConfig


class Config(AppConfig):
    name = "grandchallenge.cases"

    def ready(self):
        super().ready()

        # noinspection PyUnresolvedReferences
        import grandchallenge.cases.signals
