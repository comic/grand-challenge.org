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
def test_get_metrics(mocker):
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

    client = mocker.MagicMock()
    mocker.patch("grandchallenge.core.tasks.boto3.client", return_value=client)

    # Note, this is the format expected by CloudWatch,
    # consult the API when changing this
    result = _get_metrics()

    assert result == [
        {
            "MetricName": "JobsQueued",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsStarted",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsReQueued",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsFailed",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsSucceeded",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsCancelled",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsProvisioning",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsProvisioned",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsExecuting",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsExecuted",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsParsingOutputs",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsExecutingAlgorithm",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsExternalExecutionInProgress",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "JobsValidatinginputs",
            "Dimensions": [{"Name": "Model", "Value": "Job"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsQueued",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsStarted",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsReQueued",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsFailed",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsSucceeded",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsCancelled",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsProvisioning",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsProvisioned",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsExecuting",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsExecuted",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsParsingOutputs",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsExecutingAlgorithm",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsExternalExecutionInProgress",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EvaluationsValidatinginputs",
            "Dimensions": [{"Name": "Model", "Value": "Evaluation"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsQueued",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsStarted",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsRunning",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsFailed",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsStopped",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "SessionsExpired",
            "Dimensions": [{"Name": "Model", "Value": "Session"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsQueued",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsStarted",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsReQueued",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsFailed",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsSucceeded",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 1,
            "Unit": "Count",
        },
        {
            "MetricName": "RawImageUploadSessionsCancelled",
            "Dimensions": [
                {"Name": "Model", "Value": "RawImageUploadSession"}
            ],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "PostProcessImageTasksInitialized",
            "Dimensions": [{"Name": "Model", "Value": "PostProcessImageTask"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "PostProcessImageTasksCancelled",
            "Dimensions": [{"Name": "Model", "Value": "PostProcessImageTask"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "PostProcessImageTasksFailed",
            "Dimensions": [{"Name": "Model", "Value": "PostProcessImageTask"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "PostProcessImageTasksCompleted",
            "Dimensions": [{"Name": "Model", "Value": "PostProcessImageTask"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EndpointsQueued",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EndpointsStarted",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EndpointsRunning",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EndpointsFailed",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "EndpointsStopped",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
        {
            "MetricName": "OldestActiveAlgorithmImage",
            "Value": 0,
            "Unit": "Seconds",
        },
        {"MetricName": "OldestActiveMethod", "Value": 0, "Unit": "Seconds"},
        {
            "MetricName": "OldestActiveEvaluation",
            "Value": 0,
            "Unit": "Seconds",
        },
        {"MetricName": "OldestActiveJob", "Value": 0, "Unit": "Seconds"},
        {
            "MetricName": "OldestActiveRawImageUploadSession",
            "Value": 0,
            "Unit": "Seconds",
        },
        {"MetricName": "OldestActiveSession", "Value": 0, "Unit": "Seconds"},
        {"MetricName": "OldestActiveEndpoint", "Value": 0, "Unit": "Seconds"},
        {
            "MetricName": "LeftoverEndpointsOnSagemaker",
            "Dimensions": [{"Name": "Model", "Value": "Endpoint"}],
            "Value": 0,
            "Unit": "Count",
        },
    ]
