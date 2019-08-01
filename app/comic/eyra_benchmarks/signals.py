from django.contrib.auth.models import Group
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from guardian.shortcuts import assign_perm

from comic.core.utils import disable_for_loaddata
from comic.eyra_benchmarks.models import Benchmark, Submission
from comic.eyra_benchmarks.tasks import run_submission


@receiver(post_save, sender=Submission)
@disable_for_loaddata
def run_new_submission(
    instance: Submission = None, created: bool = False, *_, **__
):
    if created:
        run_submission.delay(str(instance.pk))


@receiver(post_save, sender=Benchmark)
@disable_for_loaddata
def setup_benchmark_admin_group(
    instance: Benchmark = None, created: bool = False, *_, **__
):
    if created:
        admin_group = Group.objects.create(name=f"{instance.name} admin")
        admin_group.save()
        instance.admin_group = admin_group
        instance.save()

        assign_perm("change_benchmark", admin_group, instance)
        assign_perm("change_group", admin_group, admin_group)

        # add current user to admins for this site
        try:
            instance.creator.groups.add(admin_group)
        except AttributeError:
            # No creator set
            pass


@receiver(post_delete, sender=Benchmark)
def delete_benchmark_admin_group(
    sender, instance, *args, **kwargs
):
    pass