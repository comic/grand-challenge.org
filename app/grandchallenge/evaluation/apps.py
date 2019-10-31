from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    name = "grandchallenge.evaluation"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.evaluation.signals  # noqa: F401
