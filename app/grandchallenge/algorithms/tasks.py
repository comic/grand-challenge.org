from tempfile import TemporaryDirectory
from typing import NamedTuple

import boto3
from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import File
from django.db import transaction
from django.db.transaction import on_commit
from django.utils._os import safe_join

from grandchallenge.algorithms.exceptions import TooManyJobsScheduled
from grandchallenge.components.tasks import lock_model_instance
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.subdomains.utils import reverse

logger = get_task_logger(__name__)


@acks_late_micro_short_task(
    retry_on=(LockNotAcquiredException, TooManyJobsScheduled)
)
@transaction.atomic
def execute_algorithm_job_for_inputs(*, job_pk):
    from grandchallenge.algorithms.models import Job

    job = lock_model_instance(
        app_label="algorithms", model_name="job", pk=job_pk
    )

    # Notify the job creator on failure
    linked_task = send_failed_job_notification.signature(
        kwargs={"job_pk": str(job.pk)}, immutable=True
    )

    if not job.inputs_complete:
        logger.info("Nothing to do, inputs are still being validated")
        return

    if not job.status == job.VALIDATING_INPUTS:
        # this task can be called multiple times with complete inputs,
        # and might have been queued for execution already, so ignore
        logger.info("Job has already been scheduled for execution")
        return

    if Job.objects.active().count() >= settings.ALGORITHMS_MAX_ACTIVE_JOBS:
        logger.info("Too many jobs scheduled")
        raise TooManyJobsScheduled

    logger.info("Job is ready, creating execution task")

    job.task_on_success = linked_task
    job.status = job.PENDING
    job.save()

    on_commit(job.execute)


def create_algorithm_jobs(
    *,
    algorithm_image,
    archive_items,
    time_limit,
    requires_gpu_type,
    requires_memory_gb,
    algorithm_model=None,
    extra_viewer_groups=None,
    extra_logs_viewer_groups=None,
    max_jobs=None,
    task_on_success=None,
    task_on_failure=None,
):
    """
    Creates algorithm jobs for sets of component interface values

    Parameters
    ----------
    algorithm_image
        The algorithm image to use
    archive_items
        Archive items whose values will be used as input
        for the algorithm image
    time_limit
        The time limit for the Job
    requires_gpu_type
        The required GPU type for the Job
    requires_memory_gb
        How much memory is required for the Job
    algorithm_model
        The algorithm model to use for the new job or None
    extra_viewer_groups
        The groups that will also get permission to view the jobs
    extra_logs_viewer_groups
        The groups that will also get permission to view the logs for
        the jobs
    max_jobs
        The maximum number of jobs to schedule
    task_on_success
        Celery task that is run on job success. This must be able
        to handle being called more than once, and in parallel.
    task_on_failure
        Celery task that is run on job failure
    """
    from grandchallenge.algorithms.models import Job

    if not algorithm_image:
        raise RuntimeError("Algorithm image required to create jobs.")

    valid_job_inputs = filter_archive_items_for_algorithm(
        archive_items=archive_items,
        algorithm_image=algorithm_image,
        algorithm_model=algorithm_model,
    )

    if time_limit is None:
        time_limit = settings.ALGORITHMS_JOB_DEFAULT_TIME_LIMIT_SECONDS

    jobs = []
    for interface, archive_items in valid_job_inputs.items():
        for ai in archive_items:
            if max_jobs is not None and len(jobs) >= max_jobs:
                # only schedule max_jobs amount of jobs
                # the rest will be scheduled only after these have succeeded
                # we do not want to retry the task here, so just stop the loop
                break

            if len(jobs) >= settings.ALGORITHMS_JOB_BATCH_LIMIT:
                # raise exception so that we retry the task
                raise TooManyJobsScheduled

            with transaction.atomic():
                job = Job.objects.create(
                    creator=None,  # System jobs, so no creator
                    algorithm_image=algorithm_image,
                    algorithm_model=algorithm_model,
                    algorithm_interface=interface,
                    task_on_success=task_on_success,
                    task_on_failure=task_on_failure,
                    time_limit=time_limit,
                    requires_gpu_type=requires_gpu_type,
                    requires_memory_gb=requires_memory_gb,
                    extra_viewer_groups=extra_viewer_groups,
                    extra_logs_viewer_groups=extra_logs_viewer_groups,
                    input_civ_set=ai.values.all(),
                )
                on_commit(job.execute)

                jobs.append(job)

    return jobs


def filter_archive_items_for_algorithm(
    *, archive_items, algorithm_image, algorithm_model=None
):
    """
    Removes archive items that are invalid for new jobs.
    The archive items need to contain values for all inputs of one of the algorithm's interfaces.

    Parameters
    ----------
    archive_items
        Archive items whose values are candidates for new jobs' inputs
    algorithm_image
        The algorithm image to use for new job
    algorithm_model
        The algorithm model to use for the new job or None

    Returns
    -------
    Dictionary of valid ArchiveItems for new jobs, grouped by AlgorithmInterface
    """
    from grandchallenge.evaluation.models import (
        get_archive_items_for_interfaces,
        get_valid_jobs_for_interfaces_and_archive_items,
    )

    algorithm_interfaces = (
        algorithm_image.algorithm.interfaces.prefetch_related("inputs").all()
    )

    # First, sort archive items by algorithm interface:
    # An archive item is only valid for an interface if it has values
    # for all inputs of the interface
    valid_job_inputs = get_archive_items_for_interfaces(
        algorithm_interfaces=algorithm_interfaces, archive_items=archive_items
    )

    # Next, group all system jobs that have been run for the provided archive items
    # with the same model and image by interface
    existing_jobs_for_interfaces = (
        get_valid_jobs_for_interfaces_and_archive_items(
            algorithm_image=algorithm_image,
            algorithm_model=algorithm_model,
            algorithm_interfaces=algorithm_interfaces,
            valid_archive_items_per_interface=valid_job_inputs,
        )
    )
    # Finally, exclude archive items for which there already is a job
    filtered_valid_job_inputs = {}
    for interface, archive_items in valid_job_inputs.items():
        job_input_sets_for_interface = {
            frozenset(j.inputs.all())
            for j in existing_jobs_for_interfaces[interface]
        }
        filtered_valid_job_inputs[interface] = [
            ai
            for ai in archive_items
            if not frozenset(ai.values.all()) in job_input_sets_for_interface
        ]

    return filtered_valid_job_inputs


@acks_late_micro_short_task
@transaction.atomic
def send_failed_job_notification(*, job_pk):
    from grandchallenge.algorithms.models import Job

    job = Job.objects.get(pk=job_pk)

    if job.status == Job.FAILURE and job.creator is not None:
        algorithm = job.algorithm_image.algorithm
        url = reverse("algorithms:job-list", kwargs={"slug": algorithm.slug})
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.JOB_STATUS,
            actor=job.creator,
            message=f"Unfortunately one of the jobs for algorithm {algorithm.title} "
            f"failed with an error",
            target=algorithm,
            description=url,
        )


class ChallengeNameAndUrl(NamedTuple):
    short_name: str
    get_absolute_url: str


@acks_late_2xlarge_task
def update_associated_challenges():
    from grandchallenge.algorithms.models import Algorithm
    from grandchallenge.challenges.models import Challenge

    challenge_list = {}
    for algorithm in Algorithm.objects.all():
        challenge_list[algorithm.pk] = [
            ChallengeNameAndUrl(
                short_name=challenge.short_name,
                get_absolute_url=challenge.get_absolute_url(),
            )
            for challenge in Challenge.objects.filter(
                phase__submission__algorithm_image__algorithm=algorithm
            ).distinct()
        ]

    cache.set("challenges_for_algorithms", challenge_list, timeout=None)


@acks_late_2xlarge_task
def import_remote_algorithm_image(*, remote_bucket_name, algorithm_image_pk):
    from grandchallenge.algorithms.models import AlgorithmImage

    algorithm_image = AlgorithmImage.objects.get(pk=algorithm_image_pk)

    if (
        algorithm_image.import_status
        != AlgorithmImage.ImportStatusChoices.INITIALIZED
    ):
        raise RuntimeError("Algorithm image is not initialized")

    s3_client = boto3.client("s3")

    try:
        response = s3_client.list_objects_v2(
            Bucket=remote_bucket_name,
            Prefix=algorithm_image.image.field.upload_to(algorithm_image, "-")[
                :-1
            ],
        )
    except ClientError as error:
        algorithm_image.import_status = (
            AlgorithmImage.ImportStatusChoices.FAILED
        )
        algorithm_image.status = str(error)
        algorithm_image.save()
        raise

    output_files = response.get("Contents", [])
    if len(output_files) != 1:
        algorithm_image.import_status = (
            AlgorithmImage.ImportStatusChoices.FAILED
        )
        algorithm_image.status = "Unique algorithm image file not found"
        algorithm_image.save()
        raise RuntimeError(algorithm_image.status)

    output_file = output_files[0]

    # We cannot copy objects directly here as this is likely a cross-region
    # request, so download it then upload
    with TemporaryDirectory() as tmp_dir:
        filename = output_file["Key"].split("/")[-1]
        dest = safe_join(tmp_dir, filename)

        s3_client.download_file(
            Filename=dest,
            Bucket=remote_bucket_name,
            Key=output_file["Key"],
        )

        with open(dest, "rb") as f:
            algorithm_image.image.save(filename, File(f))


@acks_late_micro_short_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def update_algorithm_average_duration(*, algorithm_pk):
    from grandchallenge.algorithms.models import Job

    algorithm = lock_model_instance(
        app_label="algorithms", model_name="algorithm", pk=algorithm_pk
    )

    algorithm.average_duration = Job.objects.filter(
        algorithm_image__algorithm=algorithm, status=Job.SUCCESS
    ).average_duration()
    algorithm.save(update_fields=("average_duration",))
