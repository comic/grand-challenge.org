from django.apps import AppConfig


class ParticipantsConfig(AppConfig):
    name = "grandchallenge.participants"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.participants.signals  # noqa: F401
