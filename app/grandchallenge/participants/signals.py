from actstream.actions import follow, is_following
from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.participants.models import RegistrationRequest


@receiver(post_save, sender=RegistrationRequest)
@disable_for_loaddata
def process_registration(
    instance: RegistrationRequest = None, created: bool = False, *_, **__
):
    if created and not instance.challenge.require_participant_review:
        instance.status = RegistrationRequest.ACCEPTED
        RegistrationRequest.objects.filter(pk=instance.pk).update(
            status=instance.status
        )
    elif created and instance.challenge.require_participant_review:
        Notification.send(
            type=NotificationType.NotificationTypeChoices.ACCESS_REQUEST,
            message="requested access to",
            actor=instance.user,
            target=instance.challenge,
        )
    if not is_following(instance.user, instance):
        follow(
            user=instance.user,
            obj=instance,
            actor_only=False,
            send_action=False,
        )
    if instance.status == RegistrationRequest.ACCEPTED:
        instance.challenge.add_participant(instance.user)
        Notification.send(
            type=NotificationType.NotificationTypeChoices.REQUEST_UPDATE,
            message="was approved",
            target=instance,
        )
    elif instance.status == RegistrationRequest.REJECTED:
        instance.challenge.remove_participant(instance.user)
        Notification.send(
            type=NotificationType.NotificationTypeChoices.REQUEST_UPDATE,
            message="was rejected",
            target=instance,
        )


@receiver(pre_delete, sender=RegistrationRequest)
def clean_up_request_follows(instance, **__):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(object_id=instance.pk, content_type=ct).delete()
