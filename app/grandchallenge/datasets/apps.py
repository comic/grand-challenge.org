from django.apps import AppConfig


class DatasetsConfig(AppConfig):
    name = "grandchallenge.datasets"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.datasets.signals
