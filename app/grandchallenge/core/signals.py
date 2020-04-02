from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from guardian.utils import get_anonymous_user

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.archives.models import ArchivePermissionRequest
from grandchallenge.core.emails import (
    send_permission_denied_email,
    send_permission_granted_email,
    send_permission_request_email,
)
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.reader_studies.models import ReaderStudyPermissionRequest


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
def process_permission_request(sender, instance, *_, **__):
    try:
        old_values = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        old_values = None

    old_status = old_values.status if old_values else None

    if instance.status != old_status:
        if instance.status == instance.PENDING:
            send_permission_request_email(instance)
        elif instance.status == instance.ACCEPTED:
            instance.add_method(instance.user)
            send_permission_granted_email(instance)
        else:
            instance.remove_method(instance.user)
            send_permission_denied_email(instance)
