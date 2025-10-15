from actstream.models import Follow
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.timezone import now
from guardian.shortcuts import assign_perm

from grandchallenge.discussion_forums.models import ForumPost, ForumTopic


@receiver(pre_save, sender=ForumTopic)
@receiver(pre_save, sender=ForumPost)
def disallow_spam(sender, *, instance, **_):
    account_age = now() - instance.creator.date_joined

    if account_age.days < settings.FORUMS_MIN_ACCOUNT_AGE_DAYS:
        raise PermissionDenied(
            "Your account is too new to create a forum post, "
            "please try again later"
        )


@receiver(post_save, sender=Follow)
def add_permissions(*, instance, created, **_):
    if created:
        assign_perm("change_follow", instance.user, instance)
        assign_perm("delete_follow", instance.user, instance)
        assign_perm("view_follow", instance.user, instance)
