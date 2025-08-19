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
from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    TaskCancelled,
)
from grandchallenge.components.backends.utils import LOGLINES
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.models import Evaluation, Method


@pytest.mark.parametrize(
    "memory_limit,requires_gpu_type,expected_type",
    (
        (10, GPUTypeChoices.T4, "ml.g4dn.xlarge"),
        (30, GPUTypeChoices.T4, "ml.g4dn.2xlarge"),
        (8, GPUTypeChoices.NO_GPU, "ml.m7i.large"),
        (16, GPUTypeChoices.NO_GPU, "ml.r7i.large"),
        (32, GPUTypeChoices.NO_GPU, "ml.r7i.xlarge"),
        (64, GPUTypeChoices.NO_GPU, "ml.r7i.2xlarge"),
        (128, GPUTypeChoices.NO_GPU, "ml.r7i.4xlarge"),
        (256, GPUTypeChoices.NO_GPU, "ml.r7i.8xlarge"),
        (384, GPUTypeChoices.NO_GPU, "ml.r7i.12xlarge"),
        (512, GPUTypeChoices.NO_GPU, "ml.r7i.16xlarge"),
        (768, GPUTypeChoices.NO_GPU, "ml.r7i.24xlarge"),
        (1536, GPUTypeChoices.NO_GPU, "ml.r7i.48xlarge"),
        (10, GPUTypeChoices.V100, "ml.p3.2xlarge"),
        (30, GPUTypeChoices.V100, "ml.p3.2xlarge"),
    ),
)
def test_instance_type(memory_limit, expected_type, requires_gpu_type):
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        time_limit=60,
        requires_gpu_type=requires_gpu_type,
        use_warm_pool=False,
    )

    assert executor._instance_type.name == expected_type


@pytest.mark.parametrize(
    "memory_limit,requires_gpu_type",
    (
        (13370, ""),  # Total memory unavailable
        (10, GPUTypeChoices.A100),  # GPU type not supported
        (
            100,
            GPUTypeChoices.V100,
        ),  # Amount of memory only available with multi GPU
    ),
)
def test_instance_type_incompatible(memory_limit, requires_gpu_type):
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        time_limit=60,
        requires_gpu_type=requires_gpu_type,
        use_warm_pool=False,
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
        "TrainingJobName": f"{settings.COMPONENTS_REGISTRY_PREFIX}-{key}-{pk}-00"
    }
    job_name = AmazonSageMakerTrainingExecutor.get_job_name(event=event)
    job_params = AmazonSageMakerTrainingExecutor.get_job_params(
        job_name=job_name
    )

    assert job_params.pk == str(pk)
    assert job_params.model_name == model_name
    assert job_params.app_label == app_label
    assert job_params.attempt == 0


def test_invocation_prefix():
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-0",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
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
    executor = AmazonSageMakerTrainingExecutor(**j.executor_kwargs)

    assert (
        executor._sagemaker_job_name
        == f"{settings.COMPONENTS_REGISTRY_PREFIX}-{key}-{j.pk}-00"
    )

    event = {"TrainingJobName": executor._sagemaker_job_name}
    job_name = AmazonSageMakerTrainingExecutor.get_job_name(event=event)
    job_params = AmazonSageMakerTrainingExecutor.get_job_params(
        job_name=job_name
    )

    assert job_params.pk == str(j.pk)
    assert job_params.model_name == j._meta.model_name
    assert job_params.app_label == j._meta.app_label
    assert job_params.attempt == 0


def test_invocation_json(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN = (
        "arn:aws:iam::123456789012:role/service-role/ExecutionRole"
    )

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        algorithm_model=None,
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    with Stubber(executor._sagemaker_client) as s:
        s.add_response(
            method="create_training_job",
            service_response={"TrainingJobArn": "string"},
            expected_params={
                "TrainingJobName": executor._sagemaker_job_name,
                "AlgorithmSpecification": {
                    "TrainingInputMode": "File",
                    "TrainingImage": "",
                    "ContainerArguments": [
                        "invoke",
                        "--file",
                        f"s3://grand-challenge-components-inputs//invocations/algorithms/job/{pk}/invocation.json",
                    ],
                },
                "RoleArn": settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN,
                "OutputDataConfig": {
                    "S3OutputPath": f"s3://grand-challenge-components-outputs//training-outputs/algorithms/job/{pk}"
                },
                "ResourceConfig": {
                    "VolumeSizeInGB": 30,
                    "InstanceType": "ml.m7i.large",
                    "InstanceCount": 1,
                    "KeepAlivePeriodInSeconds": 0,
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": 60},
                "Environment": {
                    "LOG_LEVEL": "INFO",
                    "PYTHONUNBUFFERED": "1",
                    "no_proxy": "amazonaws.com",
                    "GRAND_CHALLENGE_COMPONENT_WRITABLE_DIRECTORIES": "/opt/ml/output/data:/opt/ml/model:/opt/ml/input/data/ground_truth:/opt/ml/checkpoints:/tmp",
                    "GRAND_CHALLENGE_COMPONENT_POST_CLEAN_DIRECTORIES": "/opt/ml/output/data:/opt/ml/model:/opt/ml/input/data/ground_truth",
                    "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": "7168",
                },
                "VpcConfig": {
                    "SecurityGroupIds": [
                        settings.COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID
                    ],
                    "Subnets": settings.COMPONENTS_AMAZON_SAGEMAKER_SUBNETS,
                },
                "RemoteDebugConfig": {"EnableRemoteDebug": False},
            },
        )
        executor.provision(input_civs=[], input_prefixes={})

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=executor._invocation_key,
        )
        fileobj.seek(0)
        result = json.loads(fileobj.read().decode("utf-8"))

    assert result == [
        {
            "inputs": [
                {
                    "bucket_key": f"/io/algorithms/job/{pk}/inputs.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "inputs.json",
                },
            ],
            "output_bucket_name": "grand-challenge-components-outputs",
            "output_prefix": f"/io/algorithms/job/{pk}",
            "pk": f"algorithms-job-{pk}",
        }
    ]


def test_set_duration():
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-0",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    assert executor.duration is None

    executor._set_duration(
        event={
            "CreationTime": 1654683838000,
            "TrainingStartTime": 1654684027000,
            "TrainingEndTime": 1654684048000,
        }
    )

    assert executor.duration == timedelta(seconds=21)


def test_get_log_stream_name(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    with Stubber(executor._logs_client) as s:
        s.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"localhost-A-{pk}/i-whatever"},
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamNamePrefix": f"localhost-A-{pk}",
            },
        )
        log_stream_name = executor._get_log_stream_name()

    assert log_stream_name == f"localhost-A-{pk}/i-whatever"


def test_set_task_logs(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    assert executor.stdout == ""
    assert executor.stderr == ""

    with Stubber(executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"localhost-A-{pk}/i-whatever"},
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamNamePrefix": f"localhost-A-{pk}",
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
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "limit": LOGLINES,
                "startFromHead": False,
                "endTime": 1654767481000,
            },
        )
        executor._set_task_logs(
            event={
                "TrainingStartTime": 1654767467000,
                "TrainingEndTime": 1654767481000,
                "ResourceConfig": {
                    "InstanceType": "ml.m7i.large",
                    "InstanceCount": 1,
                },
            }
        )

    assert executor.stdout == "2022-06-08T10:23:58+00:00 hello from stdout"
    assert executor.stderr == "2022-06-08T10:23:58+00:00 hello from stderr"


def test_set_runtime_metrics(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
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
                        "Expression": f"SEARCH('{{/aws/sagemaker/TrainingJobs,Host}} Host=localhost-A-{pk}/algo-1', 'Average', 60)",
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
                "TrainingStartTime": 1654767467000,
                "TrainingEndTime": 1654767481000,
                "ResourceConfig": {
                    "InstanceType": "ml.m7i.large",
                    "InstanceCount": 1,
                },
            }
        )

    assert executor.runtime_metrics == {
        "instance": {
            "cpu": 2,
            "gpu_type": "",
            "gpus": 0,
            "memory": 8,
            "name": "ml.m7i.large",
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
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    return_code = 0

    with io.BytesIO() as f:
        f.write(
            json.dumps(
                {"return_code": return_code, "pk": f"algorithms-job-{pk}"}
            ).encode("utf-8")
        )
        f.seek(0)
        executor._s3_client.upload_fileobj(
            Fileobj=f,
            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            Key=executor._result_key,
        )

    assert executor._handle_completed_job() is None


def test_handle_time_limit_exceded(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    with pytest.raises(ComponentException) as error:
        executor._handle_stopped_job(
            event={
                "TrainingJobStatus": "Stopped",
                "SecondaryStatus": "MaxRuntimeExceeded",
            }
        )

    assert "Time limit exceeded" in str(error)


def test_handle_stopped_event(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
    )

    with Stubber(executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {"logStreamName": f"localhost-A-{pk}/i-whatever"},
                ]
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamNamePrefix": f"localhost-A-{pk}",
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={"events": []},
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "limit": LOGLINES,
                "startFromHead": False,
            },
        )

        with pytest.raises(TaskCancelled):
            executor.handle_event(
                event={
                    "TrainingJobStatus": "Stopped",
                    "SecondaryStatus": "Stopped",
                }
            )


def test_deprovision(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        time_limit=60,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
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
            f"{executor._training_output_prefix}/my-output.out",
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
            method="stop_training_job",
            service_response={},
            expected_params={"TrainingJobName": f"localhost-A-{pk}"},
        )
        executor.deprovision()

    for bucket, key in created_files:
        with pytest.raises(botocore.exceptions.ClientError) as error:
            executor._s3_client.head_object(
                Bucket=bucket,
                Key=key,
            )

        assert error.value.response["Error"]["Message"] == "Not Found"
