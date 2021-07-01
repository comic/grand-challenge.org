from actstream import action
from actstream.actions import follow
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from guardian.utils import get_anonymous_user

from grandchallenge.algorithms.models import (
    Algorithm,
    AlgorithmPermissionRequest,
)
from grandchallenge.archives.models import Archive, ArchivePermissionRequest
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.reader_studies.models import (
    ReaderStudy,
    ReaderStudyPermissionRequest,
)


@receiver(post_save, sender=get_user_model())
@disable_for_loaddata
def add_user_to_groups(
    instance: get_user_model = None, created: bool = False, *_, **__
):
    if created:
        g_reg_anon, _ = Group.objects.get_or_create(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )
        instance.groups.add(g_reg_anon)

        try:
            anon_pk = get_anonymous_user().pk
        except ObjectDoesNotExist:
            # Used for the next if statement, as anon does not exist
            # this user is not anonymous
            anon_pk = None

        if instance.pk != anon_pk:
            g_reg, _ = Group.objects.get_or_create(
                name=settings.REGISTERED_USERS_GROUP_NAME
            )
            instance.groups.add(g_reg)


@receiver(pre_save, sender=AlgorithmPermissionRequest)
@receiver(pre_save, sender=ArchivePermissionRequest)
@receiver(pre_save, sender=ReaderStudyPermissionRequest)
def process_permission_request_update(sender, instance, *_, **__):
    try:
        old_values = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        old_values = None

    old_status = old_values.status if old_values else None

    if instance.status != old_status:
        if instance.status == instance.ACCEPTED:
            instance.add_method(instance.user)
            action.send(
                sender=instance, verb="was accepted",
            )
        elif instance.status == instance.REJECTED:
            instance.remove_method(instance.user)
            action.send(
                sender=instance, verb="was rejected",
            )


@receiver(post_save, sender=AlgorithmPermissionRequest)
@receiver(post_save, sender=ArchivePermissionRequest)
@receiver(post_save, sender=ReaderStudyPermissionRequest)
def process_permission_request(sender, created, instance, *_, **__):
    if created:
        follow(
            user=instance.user,
            obj=instance,
            actor_only=False,
            send_action=False,
        )
        action.send(
            sender=instance.user,
            verb="requested access to",
            target=instance.base_object,
        )


@receiver(post_save, sender=Algorithm)
@receiver(post_save, sender=Archive)
@receiver(post_save, sender=ReaderStudy)
def create_editor_follows(sender, created, instance, *_, **__):
    if created:
        for user in instance.editors_group.user_set.all():
            follow(user=user, obj=instance, send_action=False)


@receiver(pre_delete, sender=Algorithm)
@receiver(pre_delete, sender=Archive)
@receiver(pre_delete, sender=ReaderStudy)
@receiver(pre_delete, sender=AlgorithmPermissionRequest)
@receiver(pre_delete, sender=ArchivePermissionRequest)
@receiver(pre_delete, sender=ReaderStudyPermissionRequest)
def delete_editor_follows(sender, instance, *_, **__):
    Follow.objects.filter(follow_object=instance).delete()
