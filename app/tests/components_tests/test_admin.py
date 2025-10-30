from datetime import timedelta

import pytest

from grandchallenge.algorithms.models import Job
from grandchallenge.components.admin import requeue_jobs
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import EvaluationFactory


@pytest.mark.parametrize("factory", (AlgorithmJobFactory, EvaluationFactory))
@pytest.mark.django_db
def test_job_reset_after_admin_requeue(factory):
    job = factory(
        time_limit=60,
        status=Job.FAILURE,
        exec_duration=timedelta(seconds=1337),
        invoke_duration=timedelta(seconds=1874),
        use_warm_pool=True,
    )
    job.utilization.duration = timedelta(minutes=1)
    job.utilization.save()

    jobs = factory._meta.model.objects.all()

    assert len(jobs) == 1
    assert job.utilization.duration is not None
    assert job.exec_duration == timedelta(seconds=1337)
    assert job.invoke_duration == timedelta(seconds=1874)
    assert job.use_warm_pool is True

    requeue_jobs(None, None, jobs)

    job.refresh_from_db()

    assert job.status == Job.RETRY
    assert job.utilization.duration is None
    assert job.exec_duration is None
    assert job.invoke_duration is None
    assert job.use_warm_pool is False
