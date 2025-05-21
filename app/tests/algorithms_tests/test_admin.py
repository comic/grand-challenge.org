from datetime import timedelta

import pytest

from grandchallenge.algorithms.models import Job
from grandchallenge.components.admin import requeue_jobs
from tests.algorithms_tests.factories import AlgorithmJobFactory


@pytest.mark.django_db
def test_job_reset_duration_after_admin_requeue():
    job = AlgorithmJobFactory(
        time_limit=60,
        status=Job.FAILURE,
    )
    job.update_utilization(duration=timedelta(minutes=1))

    jobs = Job.objects.all()

    assert len(jobs) == 1
    assert job.jobutilization.duration is not None

    requeue_jobs(None, None, jobs)

    job.refresh_from_db()

    assert job.status == Job.RETRY
    assert job.jobutilization.duration is None
