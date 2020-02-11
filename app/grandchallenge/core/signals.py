from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
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
