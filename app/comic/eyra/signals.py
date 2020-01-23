import logging
from functools import wraps

from django.contrib.auth.models import User, Group
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from comic.eyra.models import Algorithm, Submission, Benchmark, DataFile
from comic.eyra.tasks import run_submission

logger = logging.getLogger(__name__)

def disable_for_loaddata(signal_handler):
    """Decorator for disabling a signal handler when using loaddata"""

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs["raw"]:
            print(f"Skipping signal for {args} {kwargs}")
            return

        signal_handler(*args, **kwargs)

    return wrapper



@receiver(post_delete, sender=Algorithm)
def delete_algorithm_admin_group(
    sender, instance, *args, **kwargs
):
    if instance.admin_group:
        instance.admin_group.delete()


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


#todo: remove or implement
@receiver(pre_save, sender=DataFile)
@disable_for_loaddata
def set_size(
    instance: DataFile = None, *_, **__
):
    print("Should update size")


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
