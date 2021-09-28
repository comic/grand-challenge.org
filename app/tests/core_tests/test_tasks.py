import pytest

from grandchallenge.core.tasks import _get_metrics
from tests.algorithms_tests.factories import AlgorithmJobFactory
from tests.evaluation_tests.factories import EvaluationFactory
from tests.factories import SessionFactory, UploadSessionFactory


@pytest.mark.django_db
def test_get_metrics():
    AlgorithmJobFactory()
    EvaluationFactory()
    SessionFactory()
    s = UploadSessionFactory()
    s.status = s.REQUEUED
    s.save()

    # Note, this is the format expected by CloudWatch,
    # consult the API when changing this
    result = _get_metrics()

    assert result == [
        {
            "Namespace": "testserver/algorithms",
            "MetricData": [
                {"MetricName": "JobsQueued", "Value": 1, "Unit": "Count"},
                {"MetricName": "JobsStarted", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsReQueued", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsFailed", "Value": 0, "Unit": "Count"},
                {"MetricName": "JobsSucceeded", "Value": 0, "Unit": "Count"},
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
            ],
        },
        {
            "Namespace": "testserver/evaluation",
            "MetricData": [
                {
                    "MetricName": "EvaluationsQueued",
                    "Value": 1,
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
                    "Value": 0,
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
            ],
        },
        {
            "Namespace": "testserver/workstations",
            "MetricData": [
                {"MetricName": "SessionsQueued", "Value": 1, "Unit": "Count"},
                {"MetricName": "SessionsStarted", "Value": 0, "Unit": "Count"},
                {"MetricName": "SessionsRunning", "Value": 0, "Unit": "Count"},
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
                    "Value": 1,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsFailed",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsSucceeded",
                    "Value": 0,
                    "Unit": "Count",
                },
                {
                    "MetricName": "RawImageUploadSessionsCancelled",
                    "Value": 0,
                    "Unit": "Count",
                },
            ],
        },
    ]
