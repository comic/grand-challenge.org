from django.apps import AppConfig


class AlgorithmsConfig(AppConfig):
    name = "comic.eyra_algorithms"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comic.eyra_algorithms.signals
