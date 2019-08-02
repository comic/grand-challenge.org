import logging

from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from comic.core.utils import disable_for_loaddata

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
@disable_for_loaddata
def add_user_to_default_group(
    instance: User = None, created: bool = False, *_, **__
):
    if created:
        try:
            instance.groups.add(Group.objects.get(name='default'))
        except Exception as e:
            logger.error('cannot add user to default group: ' + str(e))
