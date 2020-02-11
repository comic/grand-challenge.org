from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from guardian.utils import get_anonymous_user

from grandchallenge.core.utils import disable_for_loaddata


@receiver(post_save, sender=get_user_model())
@disable_for_loaddata
def add_user_to_groups(
    instance: get_user_model = None, created: bool = False, *_, **__
):
    if created:
        g_reg_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )
        instance.groups.add(g_reg_anon)

        if instance.pk != get_anonymous_user().pk:
            g_reg = Group.objects.get(
                name=settings.REGISTERED_USERS_GROUP_NAME
            )
            instance.groups.add(g_reg)
