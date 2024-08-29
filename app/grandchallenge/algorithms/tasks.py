import logging
from tempfile import TemporaryDirectory
from typing import NamedTuple

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import File
from django.db import OperationalError, transaction
from django.db.models import Count, Q
from django.db.transaction import on_commit
from django.utils._os import safe_join

from grandchallenge.algorithms.exceptions import TooManyJobsScheduled
from grandchallenge.algorithms.models import Algorithm, AlgorithmImage, Job
from grandchallenge.archives.models import Archive
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.credits.models import Credit
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.subdomains.utils import reverse

logger = logging.getLogger(__name__)


@acks_late_micro_short_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def execute_algorithm_job_for_inputs(*, job_pk):
    queryset = Job.objects.filter(
        pk=job_pk,
    ).select_for_update(nowait=True)

    try:
        job = queryset.get()
    except OperationalError as error:
        raise LockNotAcquiredException from error

    # Notify the job creator on failure
    linked_task = send_failed_job_notification.signature(
        kwargs={"job_pk": str(job.pk)}, immutable=True
    )

    if job.inputs_complete:
        job.task_on_success = linked_task
        job.save()
        on_commit(
            execute_algorithm_job.signature(
                kwargs={"job_pk": job_pk}, immutable=True
            ).apply_async
        )
    else:
        logger.info(
            "Nothing to do: the inputs are still being created and validated."
        )
        return


@acks_late_micro_short_task(retry_on=(TooManyJobsScheduled,))
@transaction.atomic
def execute_algorithm_job(*, job_pk):
    if Job.objects.active().count() >= settings.ALGORITHMS_MAX_ACTIVE_JOBS:
        raise TooManyJobsScheduled
    else:
        job = Job.objects.get(pk=job_pk)
        on_commit(job.execute)


@acks_late_2xlarge_task(retry_on=(TooManyJobsScheduled,), singleton=True)
def create_algorithm_jobs_for_archive(
    *,
    archive_pks,
    archive_item_pks=None,
    algorithm_pks=None,
):
    if Job.objects.active().count() >= settings.ALGORITHMS_MAX_ACTIVE_JOBS:
        raise TooManyJobsScheduled

    for archive in Archive.objects.filter(pk__in=archive_pks).all():
        # Only the archive groups should be able to view the job
        # Can be shared with the algorithm editor if needed
        archive_groups = [
            archive.editors_group,
            archive.uploaders_group,
            archive.users_group,
        ]

        if algorithm_pks is not None:
            algorithms = Algorithm.objects.filter(pk__in=algorithm_pks).all()
        else:
            algorithms = archive.algorithms.all()

        if archive_item_pks is not None:
            archive_items = archive.items.filter(pk__in=archive_item_pks)
        else:
            archive_items = archive.items.all()

        for algorithm in algorithms:
            if algorithm.active_image:
                create_algorithm_jobs(
                    algorithm_image=algorithm.active_image,
                    algorithm_model=algorithm.active_model,
                    civ_sets=[
                        {*ai.values.all()}
                        for ai in archive_items.prefetch_related(
                            "values__interface"
                        )
                    ],
                    extra_viewer_groups=archive_groups,
                    # NOTE: no emails in case the logs leak data
                    # to the algorithm editors
                    task_on_success=None,
                    time_limit=algorithm.time_limit,
                )


def create_algorithm_jobs(
    *,
    algorithm_image,
    civ_sets,
    time_limit,
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
    civ_sets
        The sets of component interface values that will be used as input
        for the algorithm image
    time_limit
        The time limit for the Job
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
    if not algorithm_image:
        raise RuntimeError("Algorithm image required to create jobs.")

    civ_sets = filter_civs_for_algorithm(
        civ_sets=civ_sets,
        algorithm_image=algorithm_image,
        algorithm_model=algorithm_model,
    )

    if max_jobs is not None:
        civ_sets = civ_sets[:max_jobs]

    if time_limit is None:
        time_limit = settings.ALGORITHMS_JOB_DEFAULT_TIME_LIMIT_SECONDS

    jobs = []
    for civ_set in civ_sets:

        if len(jobs) >= settings.ALGORITHMS_JOB_BATCH_LIMIT:
            raise TooManyJobsScheduled

        with transaction.atomic():
            job = Job.objects.create(
                creator=None,  # System jobs, so no creator
                algorithm_image=algorithm_image,
                algorithm_model=algorithm_model,
                task_on_success=task_on_success,
                task_on_failure=task_on_failure,
                time_limit=time_limit,
                extra_viewer_groups=extra_viewer_groups,
                extra_logs_viewer_groups=extra_logs_viewer_groups,
                input_civ_set=civ_set,
            )
            on_commit(job.execute)

            jobs.append(job)

    return jobs


def filter_civs_for_algorithm(*, civ_sets, algorithm_image, algorithm_model):
    """
    Removes sets of civs that are invalid for new jobs

    Parameters
    ----------
    civ_sets
        Iterable of sets of ComponentInterfaceValues that are candidate for
        new Jobs
    algorithm_image
        The algorithm image to use for new job
    algorithm_model
        The algorithm model to use for the new job or None

    Returns
    -------
    Filtered set of ComponentInterfaceValues
    """
    input_interfaces = {*algorithm_image.algorithm.inputs.all()}

    existing_jobs = {
        frozenset(j.inputs.all())
        for j in Job.objects.filter(
            algorithm_image=algorithm_image, algorithm_model=algorithm_model
        )
        .annotate(
            inputs_match_count=Count(
                "inputs",
                filter=Q(
                    inputs__in={civ for civ_set in civ_sets for civ in civ_set}
                ),
            )
        )
        .filter(inputs_match_count=len(input_interfaces), creator=None)
        .prefetch_related("inputs")
    }

    valid_job_inputs = []

    for civ_set in civ_sets:
        # Check interfaces are complete
        civ_interfaces = {civ.interface for civ in civ_set}
        if input_interfaces.issubset(civ_interfaces):
            # If the algorithm works with a subset of the interfaces
            # present in the set then only feed these through to the algorithm
            valid_input = {
                civ for civ in civ_set if civ.interface in input_interfaces
            }
        else:
            continue

        # Check job has not been run
        if frozenset(valid_input) in existing_jobs:
            continue

        valid_job_inputs.append(valid_input)

    return valid_job_inputs


@acks_late_micro_short_task
@transaction.atomic
def send_failed_job_notification(*, job_pk):
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


@acks_late_2xlarge_task
def set_credits_per_job():
    default_credits_per_month = Credit._meta.get_field("credits").get_default()
    default_credits_per_job = Algorithm._meta.get_field(
        "credits_per_job"
    ).get_default()
    min_credits_per_job = (
        default_credits_per_month
        / settings.ALGORITHMS_MAX_DEFAULT_JOBS_PER_MONTH
    )

    for algorithm in Algorithm.objects.all().iterator():
        if algorithm.average_duration and algorithm.active_image:
            executor = Job(
                algorithm_image=algorithm.active_image
            ).get_executor(backend=settings.COMPONENTS_DEFAULT_BACKEND)

            cents_per_job = (
                executor.usd_cents_per_hour
                * algorithm.average_duration.total_seconds()
                / 3600
            )

            algorithm.credits_per_job = max(
                int(
                    round(
                        cents_per_job
                        * default_credits_per_month
                        / settings.ALGORITHMS_USER_CENTS_PER_MONTH,
                        -1,
                    )
                ),
                min_credits_per_job,
            )
        else:
            algorithm.credits_per_job = default_credits_per_job

        algorithm.save(update_fields=("credits_per_job",))
