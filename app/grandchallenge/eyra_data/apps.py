from django.apps import AppConfig


class EyraDataConfig(AppConfig):
    name = "grandchallenge.eyra_data"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.eyra_benchmarks.signals
