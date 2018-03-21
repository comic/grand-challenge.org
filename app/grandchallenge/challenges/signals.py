from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from evaluation.models import Config
from grandchallenge.challenges.emails import send_challenge_created_email
from grandchallenge.challenges.models import Challenge


@receiver(post_save, sender=Challenge)
def setup_challenge_groups(
    instance: Challenge = None, created: bool = False, *_, **__
):
    if created:
        # Create the evaluation config
        Config.objects.create(challenge=instance)
        # Create the groups only on first save
        admins_group = Group.objects.create(name=instance.admin_group_name())
        participants_group = Group.objects.create(
            name=instance.participants_group_name()
        )
        instance.admins_group = admins_group
        instance.participants_group = participants_group
        instance.save()

        assign_perm("change_challenge", admins_group, instance)

        # add current user to admins for this site
        try:
            instance.creator.groups.add(admins_group)
            send_challenge_created_email(instance)
        except AttributeError:
            # No creator set
            pass


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_everyone_user_group(
    instance: settings.AUTH_USER_MODEL = None, created: bool = False, *_, **__
):
    # Create the everyone usergroup when the anonymoususer is created
    if created and instance.username == settings.ANONYMOUS_USER_NAME:
        group, _ = Group.objects.get_or_create(
            name=settings.EVERYONE_GROUP_NAME
        )
        instance.groups.add(group)
