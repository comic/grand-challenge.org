from django.apps import AppConfig, apps
from django.conf import settings
from django.db.models.signals import post_migrate


def init_notification_permissions(*_, **__):
    from django.contrib.auth.models import Group
    from guardian.shortcuts import assign_perm
    from grandchallenge.notifications.models import Notification
    from actstream.models import Follow

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
        f"{Follow._meta.app_label}.delete_{Follow._meta.model_name}", g,
    )
    assign_perm(
        f"{Follow._meta.app_label}.change_{Follow._meta.model_name}", g,
    )


class NotificationsConfig(AppConfig):
    name = "grandchallenge.notifications"

    def ready(self):
        from actstream import registry

        registry.register(apps.get_model("auth.User"))
        registry.register(apps.get_model("forum.Forum"))
        registry.register(apps.get_model("forum_conversation.Topic"))
        registry.register(apps.get_model("forum_conversation.Post"))
        registry.register(apps.get_model("algorithms.Algorithm"))
        registry.register(
            apps.get_model("algorithms.AlgorithmPermissionRequest")
        )
        registry.register(apps.get_model("archives.Archive"))
        registry.register(apps.get_model("archives.ArchivePermissionRequest"))
        registry.register(apps.get_model("reader_studies.ReaderStudy"))
        registry.register(
            apps.get_model("reader_studies.ReaderStudyPermissionRequest")
        )
        registry.register(apps.get_model("challenges.Challenge"))
        registry.register(apps.get_model("challenges.ExternalChallenge"))
        registry.register(apps.get_model("participants.RegistrationRequest"))
        registry.register(apps.get_model("evaluation.Submission"))
        registry.register(apps.get_model("evaluation.Evaluation"))
        registry.register(apps.get_model("evaluation.Phase"))
        registry.register(apps.get_model("cases.RawImageUploadSession"))
        post_migrate.connect(init_notification_permissions, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.notifications.signals  # noqa: F401
