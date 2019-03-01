from django.db.models.signals import post_save
from django.dispatch import receiver

from grandchallenge.eyra_benchmarks.models import Submission

from grandchallenge.container_exec.models import (
    ContainerImageModel,
    ContainerExecJobModel,
)
from grandchallenge.container_exec.tasks import validate_docker_image_async, run_and_evaluate_algorithm_task
from grandchallenge.core.utils import disable_for_loaddata
from grandchallenge.container_exec.backends.k8s_job_submission import create_algorithm_job


@receiver(post_save, sender=Submission)
def dispatch_algorithm_run_and_evaluation(
        sender, instance: Submission = None, created: bool = False, **kwargs
):
    # Check if it is a new Submission
    # Do not remove this, as the code below actually changes and saves the Submission objects, so you'd end up with an
    # infinite recursion. Not good.
    if not created:
        return

    # Create a database Job for the submission algorithm container
    job_pk = create_algorithm_job(instance)

    # Run the submission algorithm job and evaluate the result using a Celery task
    celery_result = run_and_evaluate_algorithm_task.delay(job_pk)


@receiver(post_save)
@disable_for_loaddata
def validate_docker_image(
    instance: ContainerImageModel = None, created: bool = False, *_, **__
):
    if isinstance(instance, ContainerImageModel) and created:
        validate_docker_image_async.apply_async(
            kwargs={
                "app_label": instance._meta.app_label,
                "model_name": instance._meta.model_name,
                "pk": instance.pk,
            }
        )


@receiver(post_save)
@disable_for_loaddata
def schedule_job(
    instance: ContainerExecJobModel = None, created: bool = False, *_, **__
):
    if isinstance(instance, ContainerExecJobModel) and created:
        return instance.schedule_job()
