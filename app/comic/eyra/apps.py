from django.apps import AppConfig


class EyraConfig(AppConfig):
    name = "comic.eyra"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comic.eyra.signals
