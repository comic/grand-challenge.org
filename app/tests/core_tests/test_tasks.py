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
    assert _get_metrics() == [
        {
            "Namespace": "testserver/algorithms",
            "MetricData": [
                {"MetricName": "JobsQueued", "Value": 1, "Unit": "Count"}
            ],
        },
        {
            "Namespace": "testserver/evaluation",
            "MetricData": [
                {
                    "MetricName": "EvaluationsQueued",
                    "Value": 1,
                    "Unit": "Count",
                }
            ],
        },
        {
            "Namespace": "testserver/workstations",
            "MetricData": [
                {"MetricName": "SessionsQueued", "Value": 1, "Unit": "Count"}
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
                    "MetricName": "RawImageUploadSessionsReQueued",
                    "Value": 1,
                    "Unit": "Count",
                },
            ],
        },
    ]
