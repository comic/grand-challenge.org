from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    name = 'evaluation'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import evaluation.signals
