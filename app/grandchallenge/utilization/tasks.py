from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, transaction

from grandchallenge.algorithms.models import Job
from grandchallenge.components.backends.base import duration_to_millicents
from grandchallenge.components.tasks import check_operational_error
from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.utilization.models import JobWarmPoolUtilization


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def create_job_warm_pool_utilizations():
    try:
        jobs = list(
            Job.objects.only_completed()
            .filter(use_warm_pool=True, job_warm_pool_utilization__isnull=True)
            .select_related("job_utilization", "algorithm_image__algorithm")
            .select_for_update(
                of=("self",),
                nowait=True,
            )
            .select_for_update(
                # Lock the algorithm to avoid conflicts when updating later
                of=("algorithm_image__algorithm",),
                nowait=True,
                no_key=True,
            )
        )
    except OperationalError as error:
        check_operational_error(error)
        raise

    for job in jobs:
        executor = job.get_executor(
            backend=settings.COMPONENTS_DEFAULT_BACKEND
        )

        try:
            warm_pool_retained_billable_time_in_seconds = (
                executor.warm_pool_retained_billable_time_in_seconds
            )
        except ObjectDoesNotExist:
            if job.status == job.CANCELLED or (
                job.status == job.FAILURE
                and "was not ready to be used" in job.error_message
            ):
                # The job was never started
                warm_pool_retained_billable_time_in_seconds = 0
            else:
                raise

        if warm_pool_retained_billable_time_in_seconds is not None:
            duration = timedelta(
                seconds=warm_pool_retained_billable_time_in_seconds
            )
            JobWarmPoolUtilization.objects.create(
                job=job,
                duration=duration,
                compute_cost_euro_millicents=duration_to_millicents(
                    duration=duration,
                    usd_cents_per_hour=executor.usd_cents_per_hour,
                ),
            )
