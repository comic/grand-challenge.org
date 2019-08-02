from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from comic.core.utils import disable_for_loaddata
from comic.eyra_algorithms.models import Algorithm


@receiver(post_save, sender=Algorithm)
@disable_for_loaddata
def setup_algorithm_admin_group(
    instance: Algorithm = None, created: bool = False, *_, **__
):
    if created:
        admin_group = Group.objects.create(name=f"{instance.name} admin")
        admin_group.save()
        instance.admin_group = admin_group
        instance.save()

        assign_perm("change_algorithm", admin_group, instance)
        assign_perm("change_group", admin_group, admin_group)

        # add current user to admins for this site
        try:
            instance.creator.groups.add(admin_group)
        except AttributeError:
            # No creator set
            pass


@receiver(post_delete, sender=Algorithm)
def delete_benchmark_admin_group(
    sender, instance, *args, **kwargs
):
    pass