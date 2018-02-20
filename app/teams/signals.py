from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from teams.models import Team, TeamMember


@receiver(post_save, sender=Team)
def create_team_admin(sender: Team, instance: Team = None,
                      created: bool = False, **kwargs):
    if created and instance.creator.username != settings.ANONYMOUS_USER_NAME:
        TeamMember.objects.create(
            user=instance.creator,
            team=instance,
        )

        assign_perm('change_team', instance.creator, instance)
