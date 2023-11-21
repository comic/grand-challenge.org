from django.apps import AppConfig


class DirectMessagesConfig(AppConfig):
    name = "grandchallenge.direct_messages"

    def ready(self):
        # noinspection PyUnresolvedReferences
        import grandchallenge.direct_messages.signals  # noqa: F401
