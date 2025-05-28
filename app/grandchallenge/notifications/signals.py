from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.challenges.models import Challenge
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)
from grandchallenge.evaluation.models import Evaluation, Phase, Submission
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.participants.models import RegistrationRequest
from grandchallenge.reader_studies.models import (
    ReaderStudy,
    ReaderStudyPermissionRequest,
)


@receiver(pre_save, sender=ForumTopic)
@receiver(pre_save, sender=ForumPost)
def disallow_spam(sender, *, instance, **_):
    account_age = now() - instance.creator.date_joined

    if account_age.days < settings.FORUMS_MIN_ACCOUNT_AGE_DAYS:
        raise PermissionDenied(
            "Your account is too new to create a forum post, "
            "please try again later"
        )


@receiver(post_save, sender=ForumTopic)
def create_topic_notification(sender, *, instance, created, **_):
    if created:
        follow(
            user=instance.creator,
            obj=instance,
            actor_only=False,
            send_action=False,
        )

        if instance.kind == ForumTopicKindChoices.ANNOUNCE:
            Notification.send(
                kind=NotificationType.NotificationTypeChoices.FORUM_POST,
                actor=instance.creator,
                message="announced",
                action_object=instance,
                target=instance.forum,
                context_class="info",
            )
        else:
            Notification.send(
                kind=NotificationType.NotificationTypeChoices.FORUM_POST,
                actor=instance.creator,
                message="posted",
                action_object=instance,
                target=instance.forum,
            )


@receiver(post_save, sender=ForumPost)
def create_post_notification(sender, *, instance, created, **_):
    if created and not instance.is_alone:
        follow(
            user=instance.creator,
            obj=instance.topic,
            actor_only=False,
            send_action=False,
        )
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FORUM_POST_REPLY,
            actor=instance.creator,
            message="replied to",
            target=instance.topic,
        )


@receiver(post_save, sender=Follow)
def add_permissions(*, instance, created, **_):
    if created:
        assign_perm("change_follow", instance.user, instance)
        assign_perm("delete_follow", instance.user, instance)
        assign_perm("view_follow", instance.user, instance)


@receiver(pre_delete, sender=AlgorithmPermissionRequest)
@receiver(pre_delete, sender=ReaderStudyPermissionRequest)
@receiver(pre_delete, sender=ArchivePermissionRequest)
@receiver(pre_delete, sender=Archive)
@receiver(pre_delete, sender=Algorithm)
@receiver(pre_delete, sender=ReaderStudy)
@receiver(pre_delete, sender=Challenge)
@receiver(pre_delete, sender=Forum)
@receiver(pre_delete, sender=ForumTopic)
@receiver(pre_delete, sender=RegistrationRequest)
@receiver(pre_delete, sender=Evaluation)
@receiver(pre_delete, sender=Phase)
@receiver(pre_delete, sender=Submission)
@receiver(pre_delete, sender=RawImageUploadSession)
def clean_up_follows(*, instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(content_type=ct, object_id=instance.pk).delete()


@receiver(pre_delete, sender=AlgorithmPermissionRequest)
@receiver(pre_delete, sender=ReaderStudyPermissionRequest)
@receiver(pre_delete, sender=ArchivePermissionRequest)
@receiver(pre_delete, sender=Archive)
@receiver(pre_delete, sender=Algorithm)
@receiver(pre_delete, sender=ReaderStudy)
@receiver(pre_delete, sender=Challenge)
@receiver(pre_delete, sender=Forum)
@receiver(pre_delete, sender=ForumTopic)
@receiver(pre_delete, sender=RegistrationRequest)
@receiver(pre_delete, sender=Evaluation)
@receiver(pre_delete, sender=Phase)
@receiver(pre_delete, sender=Submission)
@receiver(pre_delete, sender=RawImageUploadSession)
def clean_up_notifications(instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Notification.objects.filter(
        Q(actor_object_id=instance.pk) & Q(actor_content_type=ct)
        | Q(action_object_object_id=instance.pk)
        & Q(action_object_content_type=ct)
        | Q(target_object_id=instance.pk) & Q(target_content_type=ct)
    ).delete()
