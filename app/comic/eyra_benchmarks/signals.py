from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from comic.core.utils import disable_for_loaddata
from comic.eyra_benchmarks.models import Benchmark, Submission
from comic.eyra_benchmarks.tasks import run_submission


@receiver(post_save, sender=Submission)
@disable_for_loaddata
def run_new_submission(
    instance: Submission = None, created: bool = False, *_, **__
):
    if created and instance:
        run_submission.delay(str(instance.pk))


@receiver(post_delete, sender=Benchmark)
def delete_benchmark_admin_group(
    sender, instance, *args, **kwargs
):
    if instance.admin_group:
        instance.admin_group.delete()
