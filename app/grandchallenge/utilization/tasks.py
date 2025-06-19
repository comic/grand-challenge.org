from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from grandchallenge.algorithms.models import Job
from grandchallenge.components.backends.base import duration_to_millicents
from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.utilization.models import JobWarmPoolUtilization


@acks_late_2xlarge_task
@transaction.atomic
def create_job_warm_pool_utilizations():
    queryset = (
        Job.objects.only_completed()
        .filter(use_warm_pool=True, job_warm_pool_utilization__isnull=True)
        .select_related("job_utilization", "algorithm_image")
    )

    for job in queryset:
        executor = job.get_executor(
            backend=settings.COMPONENTS_DEFAULT_BACKEND
        )

        try:
            warm_pool_retained_billable_time_in_seconds = (
                executor.warm_pool_retained_billable_time_in_seconds
            )
        except ObjectDoesNotExist:
            if job.status == job.CANCELLED:
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
