from datetime import timedelta

import pytest
from django.utils import timezone

from grandchallenge.algorithms.models import Job as AlgorithmJob
from grandchallenge.components.tasks import mark_long_running_jobs_failed
from grandchallenge.evaluation.models import Evaluation as EvaluationJob
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import EvaluationFactory


@pytest.mark.django_db
def test_mark_long_running_jobs_failed():
    # Started jobs should be unaffected
    j1 = EvaluationFactory()
    j1.update_status(status=EvaluationJob.EXECUTING)

    # Long running jobs should be marked as failed
    j2 = EvaluationFactory()
    j2.update_status(status=EvaluationJob.EXECUTING)
    j2.started_at = timezone.now() - timedelta(days=1)
    j2.save()

    # A job that has not been started should not be marked as failed, even if
    # if it is outside the celery task limit
    j3 = EvaluationFactory()
    j3.created -= timedelta(days=1)
    j3.save()

    # Algorithm jobs should not be affected
    a = AlgorithmJobFactory()
    a.update_status(status=AlgorithmJob.EXECUTING)

    assert EvaluationJob.objects.all().count() == 3
    assert (
        AlgorithmJob.objects.filter(status=AlgorithmJob.EXECUTING).count() == 1
    )
    assert (
        EvaluationJob.objects.filter(status=EvaluationJob.FAILURE).count() == 0
    )

    assert j1.status == EvaluationJob.EXECUTING
    assert j2.status == EvaluationJob.EXECUTING
    assert j3.status == EvaluationJob.PENDING
    assert a.status == AlgorithmJob.EXECUTING

    mark_long_running_jobs_failed(
        app_label="evaluation", model_name="evaluation"
    )

    j1.refresh_from_db()
    j2.refresh_from_db()
    j3.refresh_from_db()
    a.refresh_from_db()

    assert j1.status == EvaluationJob.EXECUTING
    assert j2.status == EvaluationJob.FAILURE
    assert j3.status == EvaluationJob.PENDING
    assert a.status == AlgorithmJob.EXECUTING
