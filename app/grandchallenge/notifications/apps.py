from django.apps import AppConfig, apps


class NotificationsConfig(AppConfig):
    name = "grandchallenge.notifications"

    def ready(self):
        from actstream import registry

        registry.register(apps.get_model("auth.User"))
        registry.register(apps.get_model("forum.Forum"))
        registry.register(apps.get_model("forum_conversation.Topic"))
        registry.register(apps.get_model("forum_conversation.Post"))

        # noinspection PyUnresolvedReferences
        import grandchallenge.notifications.signals  # noqa: F401
