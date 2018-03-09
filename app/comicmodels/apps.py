from django.apps import AppConfig


class ComicModelsConfig(AppConfig):
    name = 'comicmodels'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import comicmodels.signals
