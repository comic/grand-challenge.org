from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from grandchallenge.challenges.emails import (
    send_challenge_created_email,
    send_external_challenge_created_email,
)
from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.datasets.models import ImageSet
from grandchallenge.evaluation.models import Config


@receiver(post_save, sender=Challenge)
@disable_for_loaddata
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

        # Create the datasets
        ImageSet.objects.create(phase=ImageSet.TESTING, challenge=instance)
        ImageSet.objects.create(phase=ImageSet.TRAINING, challenge=instance)

        # add current user to admins for this challenge
        try:
            instance.creator.groups.add(admins_group)
        except AttributeError:
            # No creator set
            pass

        send_challenge_created_email(instance)


@receiver(post_save, sender=ExternalChallenge)
@disable_for_loaddata
def setup_external_challenge(
    instance: ExternalChallenge = None, created: bool = False, *_, **__
):
    if created:
        send_external_challenge_created_email(instance)
