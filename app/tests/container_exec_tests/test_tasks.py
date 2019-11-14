from datetime import timedelta

import pytest

from grandchallenge.algorithms.models import Job as AlgorithmJob
from grandchallenge.container_exec.tasks import mark_long_running_jobs_failed
from grandchallenge.evaluation.models import Job as EvaluationJob
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.factories import JobFactory as EvaluationJobFactory


@pytest.mark.django_db
def test_mark_long_running_jobs_failed():
    # Started jobs should be unaffected
    EvaluationJobFactory(status=EvaluationJob.STARTED)

    # Long running jobs should be marked as failed
    j2 = EvaluationJobFactory(status=EvaluationJob.STARTED)
    j2.created -= timedelta(days=1)
    j2.save()

    # A job that has not been started should not be marked as failed, even if
    # if it is outside the celery task limit
    j3 = EvaluationJobFactory()
    j3.created -= timedelta(days=1)
    j3.save()

    # Algorithm jobs should not be affected
    AlgorithmJobFactory(status=AlgorithmJob.STARTED)

    assert EvaluationJob.objects.all().count() == 3
    assert (
        AlgorithmJob.objects.filter(status=AlgorithmJob.STARTED).count() == 1
    )

    mark_long_running_jobs_failed(app_label="evaluation", model_name="job")

    assert (
        EvaluationJob.objects.filter(status=EvaluationJob.STARTED).count() == 1
    )
    assert (
        EvaluationJob.objects.filter(status=EvaluationJob.PENDING).count() == 1
    )
    assert (
        AlgorithmJob.objects.filter(status=AlgorithmJob.STARTED).count() == 1
    )
