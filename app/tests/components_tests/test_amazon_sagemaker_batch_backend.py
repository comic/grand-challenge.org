import io
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from botocore.stub import Stubber
from django.conf import settings

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.components.backends.amazon_sagemaker_batch import (
    AmazonSageMakerBatchExecutor,
)
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
