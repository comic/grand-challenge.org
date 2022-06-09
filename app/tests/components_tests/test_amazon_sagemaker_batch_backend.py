import io
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import botocore
import pytest
from botocore.stub import Stubber
from dateutil.tz import tzlocal
from django.conf import settings

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.components.backends.amazon_sagemaker_batch import (
    AmazonSageMakerBatchExecutor,
)
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    TaskCancelled,
)
from grandchallenge.components.backends.utils import LOGLINES
from grandchallenge.evaluation.models import Evaluation, Method


@pytest.mark.parametrize(
    "memory_limit,requires_gpu,expected_type",
    (
        (10, True, "ml.g4dn.xlarge"),
        (30, True, "ml.g4dn.2xlarge"),
        (6, False, "ml.m5.large"),
        (10, False, "ml.m5.xlarge"),
        (30, False, "ml.m5.2xlarge"),
    ),
)
def test_instance_type(memory_limit, requires_gpu, expected_type):
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        time_limit=60,
        requires_gpu=requires_gpu,
    )

    assert executor._instance_type == expected_type


def test_instance_type_incompatible():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=1337,
        time_limit=60,
        requires_gpu=False,
    )

    with pytest.raises(ValueError):
        _ = executor._instance_type


@pytest.mark.parametrize(
    "key,model_name,app_label",
    (
        ("A", "job", "algorithms"),
        ("E", "evaluation", "evaluation"),
    ),
)
def test_get_job_params_match(key, model_name, app_label):
    pk = uuid4()
    event = {
        "TransformJobName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-{key}-{pk}"
    }
    job_params = AmazonSageMakerBatchExecutor.get_job_params(event=event)

    assert job_params.pk == str(pk)
    assert job_params.model_name == model_name
    assert job_params.app_label == app_label


def test_invocation_prefix():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-0",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    # The id of the job must be in the prefixes
    assert executor._invocation_prefix == "/invocations/algorithms/job/0"
    assert executor._io_prefix == "/io/algorithms/job/0"
    assert (
        executor._invocation_key
        == "/invocations/algorithms/job/0/invocation.json"
    )
    # The invocations and io must not overlap
    assert executor._io_prefix != executor._invocation_prefix


@pytest.mark.parametrize(
    "model,container,container_model,key",
    (
        (Job, "algorithm_image", AlgorithmImage, "A"),
        (Evaluation, "method", Method, "E"),
    ),
)
def test_transform_job_name(model, container, container_model, key):
    j = model(pk=uuid4())
    setattr(j, container, container_model(pk=uuid4()))
    executor = AmazonSageMakerBatchExecutor(**j.executor_kwargs)

    assert (
        executor._transform_job_name
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-{key}-{j.pk}"
    )

    event = {"TransformJobName": executor._transform_job_name}
    job_params = AmazonSageMakerBatchExecutor.get_job_params(event=event)

    assert job_params.pk == str(j.pk)
    assert job_params.model_name == j._meta.model_name
    assert job_params.app_label == j._meta.app_label


def test_execute(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    with Stubber(executor._sagemaker_client) as s:
        s.add_response(
            method="create_transform_job",
            service_response={"TransformJobArn": "string"},
            expected_params={
                "TransformJobName": executor._transform_job_name,
                "Environment": {"LOGLEVEL": "INFO"},
                "ModelClientConfig": {
                    "InvocationsMaxRetries": 0,
                    "InvocationsTimeoutInSeconds": 60,
                },
                "ModelName": "",
                "TransformInput": {
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": f"s3://grand-challenge-components-inputs//invocations/algorithms/job/{pk}/invocation.json",
                        }
                    }
                },
                "TransformOutput": {
                    "S3OutputPath": f"s3://grand-challenge-components-outputs//invocations/algorithms/job/{pk}"
                },
                "TransformResources": {
                    "InstanceCount": 1,
                    "InstanceType": "ml.m5.large",
                },
            },
        )
        executor.execute(input_civs=[], input_prefixes={})

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=executor._invocation_key,
        )
        fileobj.seek(0)
        result = json.loads(fileobj.read().decode("utf-8"))

    assert result == {
        "inputs": [],
        "output_bucket_name": "grand-challenge-components-outputs",
        "output_prefix": f"/io/algorithms/job/{pk}",
        "pk": f"algorithms-job-{pk}",
    }


def test_set_duration():
    executor = AmazonSageMakerBatchExecutor(
        job_id="algorithms-job-0",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    assert executor.duration is None

    executor._set_duration(
        event={
            "CreationTime": 1654683838000,
            "TransformStartTime": 1654684027000,
            "TransformEndTime": 1654684048000,
        }
    )

    assert executor.duration == timedelta(seconds=21)


@pytest.mark.parametrize("data_log", (True, False))
def test_get_log_stream_name(settings, data_log):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    with Stubber(executor._logs_client) as s:
        s.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"gc.localhost-A-{pk}/i-whatever"},
                    {
                        "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log"
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamNamePrefix": f"gc.localhost-A-{pk}",
            },
        )
        log_stream_name = executor._get_log_stream_name(data_log=data_log)

    if data_log:
        assert log_stream_name == f"gc.localhost-A-{pk}/i-whatever/data-log"
    else:
        assert log_stream_name == f"gc.localhost-A-{pk}/i-whatever"


def test_set_task_logs(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    assert executor.stdout == ""
    assert executor.stderr == ""

    with Stubber(executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"gc.localhost-A-{pk}/i-whatever"},
                    {
                        "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log"
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamNamePrefix": f"gc.localhost-A-{pk}",
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={
                "events": [
                    {
                        "message": json.dumps(
                            {
                                "log": "hello from stdout",
                                "source": "stdout",
                                "internal": False,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "hello from stderr",
                                "source": "stderr",
                                "internal": False,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "internal stderr",
                                "source": "stderr",
                                "internal": True,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "internal stdout",
                                "source": "stdout",
                                "internal": True,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": "unstructured log",
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps({"err": "wrong"}),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "wrong source",
                                "source": "fdgfgsdfdg",
                                "internal": False,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamName": f"gc.localhost-A-{pk}/i-whatever",
                "limit": LOGLINES,
                "startFromHead": False,
            },
        )
        executor._set_task_logs()

    assert executor.stdout == "2022-06-08T10:23:58+00:00 hello from stdout"
    assert executor.stderr == "2022-06-08T10:23:58+00:00 hello from stderr"


def test_get_job_data_log(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    with Stubber(executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"gc.localhost-A-{pk}/i-whatever"},
                    {
                        "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log"
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamNamePrefix": f"gc.localhost-A-{pk}",
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={
                "events": [
                    {
                        "message": "data message",
                        "timestamp": 1654683838000,
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log",
                "limit": LOGLINES,
                "startFromHead": False,
            },
        )

        data_logs = executor._get_job_data_log()

    assert data_logs == ["data message"]


def test_set_runtime_metrics(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    assert executor.runtime_metrics == {}

    with Stubber(executor._cloudwatch_client) as cloudwatch:
        cloudwatch.add_response(
            method="get_metric_data",
            service_response={
                "MetricDataResults": [
                    {
                        "Id": "q",
                        "Label": "CPUUtilization",
                        "Timestamps": [
                            datetime(2022, 6, 9, 9, 38, tzinfo=tzlocal()),
                            datetime(2022, 6, 9, 9, 37, tzinfo=tzlocal()),
                        ],
                        "Values": [0.677884, 0.130367],
                        "StatusCode": "Complete",
                    },
                    {
                        "Id": "q",
                        "Label": "MemoryUtilization",
                        "Timestamps": [
                            datetime(2022, 6, 9, 9, 38, tzinfo=tzlocal()),
                            datetime(2022, 6, 9, 9, 37, tzinfo=tzlocal()),
                        ],
                        "Values": [1.14447, 0.875619],
                        "StatusCode": "Complete",
                    },
                ]
            },
            expected_params={
                "EndTime": datetime(2022, 6, 9, 9, 43, 1, tzinfo=timezone.utc),
                "MetricDataQueries": [
                    {
                        "Expression": f"SEARCH('{{/aws/sagemaker/TransformJobs,Host}} Host=gc.localhost-A-{pk}/i-', 'Average', 60)",
                        "Id": "q",
                    }
                ],
                "StartTime": datetime(
                    2022, 6, 9, 9, 36, 47, tzinfo=timezone.utc
                ),
            },
        )
        executor._set_runtime_metrics(
            event={
                "TransformStartTime": 1654767467000,
                "TransformEndTime": 1654767481000,
                "TransformResources": {
                    "InstanceType": "ml.m5.large",
                    "InstanceCount": 1,
                },
            }
        )

    assert executor.runtime_metrics == {
        "instance": {
            "cpu": 2,
            "gpu_type": None,
            "gpus": 0,
            "memory": 8,
            "name": "ml.m5.large",
            "price_per_hour": 0.128,
        },
        "metrics": [
            {
                "label": "CPUUtilization",
                "status": "Complete",
                "timestamps": [
                    "2022-06-09T09:38:00+00:00",
                    "2022-06-09T09:37:00+00:00",
                ],
                "values": [0.677884, 0.130367],
            },
            {
                "label": "MemoryUtilization",
                "status": "Complete",
                "timestamps": [
                    "2022-06-09T09:38:00+00:00",
                    "2022-06-09T09:37:00+00:00",
                ],
                "values": [1.14447, 0.875619],
            },
        ],
    }


def test_handle_completed_job():
    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    return_code = 0

    with io.BytesIO() as f:
        f.write(json.dumps({"return_code": return_code}).encode("utf-8"))
        f.seek(0)
        executor._s3_client.upload_fileobj(
            Fileobj=f,
            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            Key=f"{executor._invocation_key}.out",
        )

    assert executor._handle_completed_job() is None


def test_handle_failed_job(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    with Stubber(executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"gc.localhost-A-{pk}/i-whatever"},
                    {
                        "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log"
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamNamePrefix": f"gc.localhost-A-{pk}",
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={
                "events": [
                    {
                        "message": "Something happened",
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": "Model server did not respond to /invocations request within 1200 seconds",
                        "timestamp": 1654683838000,
                    },
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TransformJobs",
                "logStreamName": f"gc.localhost-A-{pk}/i-whatever/data-log",
                "limit": LOGLINES,
                "startFromHead": False,
            },
        )

        with pytest.raises(ComponentException) as error:
            executor._handle_failed_job()

    assert "Time limit exceeded" in str(error)


def test_handle_stopped_event():
    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    with pytest.raises(TaskCancelled):
        executor.handle_event(event={"TransformJobStatus": "Stopped"})


def test_deprovision(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerBatchExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu=False,
    )

    created_files = (
        (
            settings.COMPONENTS_INPUT_BUCKET_NAME,
            f"{executor._io_prefix}/test.json",
        ),
        (
            settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            f"{executor._io_prefix}/test.json",
        ),
        (settings.COMPONENTS_INPUT_BUCKET_NAME, executor._invocation_key),
        (
            settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            f"{executor._invocation_key}.out",
        ),
    )

    for bucket, key in created_files:
        with io.BytesIO() as f:
            f.write(json.dumps({"foo": 123}).encode("utf-8"))
            executor._s3_client.upload_fileobj(
                Fileobj=f,
                Bucket=bucket,
                Key=key,
            )

    with Stubber(executor._sagemaker_client) as s:
        s.add_response(
            method="stop_transform_job",
            service_response={},
            expected_params={"TransformJobName": f"gc.localhost-A-{pk}"},
        )
        executor.deprovision()

    for bucket, key in created_files:
        with pytest.raises(botocore.exceptions.ClientError) as error:
            executor._s3_client.head_object(
                Bucket=bucket,
                Key=key,
            )

        assert error.value.response["Error"]["Message"] == "Not Found"
