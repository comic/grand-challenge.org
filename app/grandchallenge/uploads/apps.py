from django.apps import AppConfig


class UploadsConfig(AppConfig):
    name = 'grandchallenge.uploads'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.uploads.signals
