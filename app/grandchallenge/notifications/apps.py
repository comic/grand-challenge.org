from django.apps import AppConfig, apps
from django.db.models.signals import post_migrate

from config import settings


def init_notification_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.notifications.models import Notification

    g, _ = Group.objects.get_or_create(
        name=settings.REGISTERED_USERS_GROUP_NAME
    )
    assign_perm(
        f"{Notification._meta.app_label}.change_{Notification._meta.model_name}",
        g,
    )
    assign_perm(
        f"{Notification._meta.app_label}.delete_{Notification._meta.model_name}",
        g,
    )
    assign_perm(
        f"{Notification._meta.app_label}.view_{Notification._meta.model_name}",
        g,
    )


class NotificationsConfig(AppConfig):
    name = "grandchallenge.notifications"

    def ready(self):
        from actstream import registry

        registry.register(apps.get_model("auth.User"))
        registry.register(apps.get_model("forum.Forum"))
        registry.register(apps.get_model("forum_conversation.Topic"))
        registry.register(apps.get_model("forum_conversation.Post"))
        post_migrate.connect(init_notification_permissions, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.notifications.signals  # noqa: F401
