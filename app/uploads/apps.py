from django.apps import AppConfig


class UploadsConfig(AppConfig):
    name = 'uploads'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import uploads.signals
