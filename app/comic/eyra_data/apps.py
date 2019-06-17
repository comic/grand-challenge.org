from django.apps import AppConfig


class EyraDataConfig(AppConfig):
    name = "comic.eyra_data"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comic.eyra_benchmarks.signals
