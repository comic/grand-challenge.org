import pytest

from grandchallenge.algorithms.models import AlgorithmImage
from grandchallenge.core.tasks import _get_metrics
from grandchallenge.evaluation.models import Method
from tests.algorithms_tests.factories import (
    AlgorithmImageFactory,
    AlgorithmJobFactory,
)
from tests.evaluation_tests.factories import EvaluationFactory, MethodFactory
from tests.factories import SessionFactory, UploadSessionFactory


@pytest.mark.django_db
def test_get_metrics():
    ai = AlgorithmImageFactory(
        import_status=AlgorithmImage.ImportStatusChoices.COMPLETED
    )

    a = AlgorithmJobFactory(
        algorithm_image=ai, time_limit=ai.algorithm.time_limit
    )
    a.status = a.SUCCESS
    a.save()

    m = MethodFactory(import_status=Method.ImportStatusChoices.COMPLETED)

    e = EvaluationFactory(method=m, time_limit=m.phase.evaluation_time_limit)
    e.status = e.SUCCESS
    e.save()

    s = SessionFactory()
    s.status = s.RUNNING
    s.save()

    s = UploadSessionFactory()
    s.status = s.SUCCESS
    s.save()

    # Note, this is the format expected by CloudWatch,
    # consult the API when changing this
    result = _get_metrics()

    assert result == [
        {
            "Namespace": "testserver/algorithms",
            "MetricData": [
                {"MetricName": "JobsQueued", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsStarted", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsReQueued", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsFailed", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsSucceeded", "Value": 1, "Unit": "Count"},
                {"MetricName": "JobsCancelled", "Value": 0, "Unit": "Count"},
                {
                    "MetricName": "JobsProvisioning",
                    "Value": 0,
                    "Unit": "Count",
                },
                {"MetricName": "JobsProvisioned", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsExecuting", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsExecuted", "Value": 0, "Unit": "Count"},
                {
                    "MetricName": "JobsParsingOutputs",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "JobsExecutingAlgorithm",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "JobsExternalExecutionInProgress",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "JobsValidatinginputs",
                    "Value": 0,
                    "Unit": "Count",
                },
            ],
        },
        {
            "Namespace": "testserver/evaluation",
            "MetricData": [
                {
                    "MetricName": "EvaluationsQueued",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsStarted",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsReQueued",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsFailed",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsSucceeded",
                    "Value": 1,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsCancelled",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsProvisioning",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsProvisioned",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsExecuting",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsExecuted",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsParsingOutputs",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsExecutingAlgorithm",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsExternalExecutionInProgress",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "EvaluationsValidatinginputs",
                    "Value": 0,
                    "Unit": "Count",
                },
            ],
        },
        {
            "Namespace": "testserver/workstations",
            "MetricData": [
                {"MetricName": "SessionsQueued", "Value": 0, "Unit": "Count"},
                {"MetricName": "SessionsStarted", "Value": 0, "Unit": "Count"},
                {"MetricName": "SessionsRunning", "Value": 1, "Unit": "Count"},
                {"MetricName": "SessionsFailed", "Value": 0, "Unit": "Count"},
                {"MetricName": "SessionsStopped", "Value": 0, "Unit": "Count"},
            ],
        },
        {
            "Namespace": "testserver/cases",
            "MetricData": [
                {
                    "MetricName": "RawImageUploadSessionsQueued",
                    "Value": 1,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsStarted",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsReQueued",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsFailed",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsSucceeded",
                    "Value": 1,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsCancelled",
                    "Value": 0,
                    "Unit": "Count",
                },
            ],
        },
        {
            "MetricData": [
                {
                    "MetricName": "PostProcessImageTasksInitialized",
                    "Unit": "Count",
                    "Value": 0,
                },
                {
                    "MetricName": "PostProcessImageTasksCancelled",
                    "Unit": "Count",
                    "Value": 0,
                },
                {
                    "MetricName": "PostProcessImageTasksFailed",
                    "Unit": "Count",
                    "Value": 0,
                },
                {
                    "MetricName": "PostProcessImageTasksCompleted",
                    "Unit": "Count",
                    "Value": 0,
                },
            ],
            "Namespace": "testserver/cases",
        },
        {
            "Namespace": "testserver/AsyncTasks",
            "MetricData": [
                {
                    "MetricName": "OldestActiveAlgorithmImage",
                    "Unit": "Seconds",
                    "Value": 0,
                },
                {
                    "MetricName": "OldestActiveMethod",
                    "Unit": "Seconds",
                    "Value": 0,
                },
                {
                    "MetricName": "OldestActiveEvaluation",
                    "Unit": "Seconds",
                    "Value": 0,
                },
                {
                    "MetricName": "OldestActiveJob",
                    "Unit": "Seconds",
                    "Value": 0,
                },
                {
                    "MetricName": "OldestActiveRawImageUploadSession",
                    "Unit": "Seconds",
                    "Value": 0,
                },
                {
                    "MetricName": "OldestActiveSession",
                    "Unit": "Seconds",
                    "Value": 0,
                },
            ],
        },
    ]
