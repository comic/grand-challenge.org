from django.apps import AppConfig


class EvaluationConfig(AppConfig):
    name = "grandchallenge.verifications"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.verifications.signals  # noqa: F401
