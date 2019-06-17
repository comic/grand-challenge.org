from django.apps import AppConfig


class BenchmarksConfig(AppConfig):
    name = "comic.eyra_benchmarks"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comic.eyra_benchmarks.signals
