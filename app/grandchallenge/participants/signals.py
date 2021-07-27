from actstream import action
from actstream.actions import follow, is_following
from actstream.models import Follow
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from grandchallenge.core.utils import disable_for_loaddata
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
        action.send(
            sender=instance.user,
            verb="requested access to",
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
        action.send(
            sender=instance, verb="was approved",
        )
    elif instance.status == RegistrationRequest.REJECTED:
        instance.challenge.remove_participant(instance.user)
        action.send(
            sender=instance, verb="was rejected",
        )


@receiver(pre_delete, sender=RegistrationRequest)
def clean_up_request_follows(instance, **__):
    Follow.objects.filter(object_id=instance.pk).delete()
