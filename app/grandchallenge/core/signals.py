from actstream.actions import follow, unfollow
from actstream.models import Follow
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models.signals import (
    m2m_changed,
    post_save,
    pre_delete,
    pre_save,
)
from django.dispatch import receiver
from guardian.utils import get_anonymous_user

from grandchallenge.algorithms.models import AlgorithmPermissionRequest
from grandchallenge.archives.models import ArchivePermissionRequest
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.notifications.models import Notification, NotificationType
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
def process_permission_request_update(sender, instance, *_, **__):
    try:
        old_values = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        old_values = None

    old_status = old_values.status if old_values else None

    if instance.status != old_status:
        if instance.status == instance.ACCEPTED:
            instance.add_method(instance.user)
            Notification.send(
                type=NotificationType.NotificationTypeChoices.REQUEST_UPDATE,
                verb="was accepted",
                target=instance,
            )
        elif instance.status == instance.REJECTED:
            instance.remove_method(instance.user)
            Notification.send(
                type=NotificationType.NotificationTypeChoices.REQUEST_UPDATE,
                verb="was rejected",
                target=instance,
            )


@receiver(m2m_changed, sender=Group.user_set.through)
def update_editor_follows(  # noqa: C901
    instance, action, reverse, model, pk_set, **_
):  # noqa: C901

    if action not in ["post_add", "pre_remove", "pre_clear"]:
        # nothing to do for the other actions
        return

    if reverse:
        groups = [instance]
        if pk_set is None:
            users = instance.user_set.all()
        else:
            users = model.objects.filter(pk__in=pk_set).all()
    else:
        if pk_set is None:
            groups = instance.groups.all()
        else:
            groups = model.objects.filter(pk__in=pk_set).all()
        users = [instance]

    follow_objects = []
    for group in groups:
        if hasattr(group, "editors_of_algorithm"):
            follow_objects.append(group.editors_of_algorithm)
        elif hasattr(group, "editors_of_archive"):
            follow_objects.append(group.editors_of_archive)
        elif hasattr(group, "editors_of_readerstudy"):
            follow_objects.append(group.editors_of_readerstudy)
        elif hasattr(group, "admins_of_challenge"):
            # NOTE: only admins of a challenge should follow a challenge
            # and its phases
            follow_objects.append(group.admins_of_challenge)
            for phase in group.admins_of_challenge.phase_set.all():
                follow_objects.append(phase)

    for user in users:
        for obj in follow_objects:
            if action == "post_add":
                follow(
                    user=user, obj=obj, actor_only=False, send_action=False,
                )
                # only new admins of a challenge get notified
                if obj._meta.model_name == "challenge":
                    Notification.send(
                        type=NotificationType.NotificationTypeChoices.NEW_ADMIN,
                        verb="added as admin for",
                        action_object=user,
                        target=obj,
                    )
            elif action == "pre_remove" or action == "pre_clear":
                unfollow(user=user, obj=obj, send_action=False)


@receiver(pre_delete, sender=get_user_model())
def clean_up_user_follows(instance, **_):
    ct = ContentType.objects.filter(
        app_label=instance._meta.app_label, model=instance._meta.model_name
    ).get()
    Follow.objects.filter(
        Q(object_id=instance.pk) | Q(user=instance.pk), content_type=ct
    ).delete()
