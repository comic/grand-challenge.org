from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate


def init_notification_permissions(*_, **__):
    from actstream.models import Follow
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
        f"{Follow._meta.app_label}.delete_{Follow._meta.model_name}", g
    )
    assign_perm(
        f"{Follow._meta.app_label}.change_{Follow._meta.model_name}", g
    )


class NotificationsConfig(AppConfig):
    name = "grandchallenge.notifications"

    def ready(self):
        from actstream import registry

        from grandchallenge.algorithms.models import (
            Algorithm,
            AlgorithmPermissionRequest,
        )
        from grandchallenge.archives.models import (
            Archive,
            ArchivePermissionRequest,
        )
        from grandchallenge.cases.models import (
            DICOMImageSetUpload,
            RawImageUploadSession,
        )
        from grandchallenge.challenges.models import Challenge
        from grandchallenge.discussion_forums.models import (
            Forum,
            ForumPost,
            ForumTopic,
        )
        from grandchallenge.evaluation.models import (
            Evaluation,
            Phase,
            Submission,
        )
        from grandchallenge.participants.models import RegistrationRequest
        from grandchallenge.reader_studies.models import (
            ReaderStudy,
            ReaderStudyPermissionRequest,
        )

        registry.register(get_user_model())
        registry.register(Algorithm)
        registry.register(AlgorithmPermissionRequest)
        registry.register(Archive)
        registry.register(ArchivePermissionRequest)
        registry.register(ReaderStudy)
        registry.register(ReaderStudyPermissionRequest)
        registry.register(Challenge)
        registry.register(RegistrationRequest)
        registry.register(Submission)
        registry.register(Evaluation)
        registry.register(Phase)
        registry.register(RawImageUploadSession)
        registry.register(DICOMImageSetUpload)
        registry.register(Forum)
        registry.register(ForumTopic)
        registry.register(ForumPost)
        post_migrate.connect(init_notification_permissions, sender=self)

        # noinspection PyUnresolvedReferences
        import grandchallenge.notifications.signals  # noqa: F401
