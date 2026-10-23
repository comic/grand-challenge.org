import hashlib
import hmac
import io
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import botocore
import pytest
from botocore.stub import Stubber
from dateutil.tz import tzlocal
from django.conf import settings
from django.utils._os import safe_join
from django.utils.timezone import now

from grandchallenge.algorithms.models import AlgorithmImage, Job
from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
    AmazonSageMakerTrainingLogsService,
    ParsedLog,
    SourceChoices,
)
from grandchallenge.components.backends.base import (
    InferenceResult,
    InferenceTaskDefinition,
    RuntimeSetupResult,
)
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    TaskCancelled,
    UncleanExit,
)
from grandchallenge.components.models import APIMethodChoices
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.tasks import execute_job, handle_event
from grandchallenge.core.error_messages import SystemErrorMessages
from grandchallenge.evaluation.models import BatchJob, Evaluation, Method
from tests.algorithms_tests.factories import (
    AlgorithmJobFactory,
    AlgorithmModelFactory,
)
from tests.components_tests.factories import ComponentInterfaceValueFactory
from tests.evaluation_tests.factories import BatchJobFactory


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
        (10, GPUTypeChoices.A100, "ml.p4d.24xlarge"),
        (100, GPUTypeChoices.V100, "ml.p3.8xlarge"),
    ),
)
def test_instance_type(memory_limit, expected_type, requires_gpu_type):
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        requires_gpu_type=requires_gpu_type,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
    )

    assert executor._instance_type.name == expected_type


@pytest.mark.parametrize(
    "memory_limit,requires_gpu_type",
    (
        (13370, GPUTypeChoices.NO_GPU),
        (13370, GPUTypeChoices.T4),
    ),
)
def test_instance_type_incompatible(memory_limit, requires_gpu_type):
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-00000000-0000-0000-0000-000000000000",
        exec_image_repo_tag="",
        memory_limit=memory_limit,
        requires_gpu_type=requires_gpu_type,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
    )

    with pytest.raises(ValueError):
        _ = executor._instance_type


@pytest.mark.parametrize(
    "key,model_name,app_label",
    (
        ("A", "job", "algorithms"),
        ("E", "evaluation", "evaluation"),
        ("B", "batchjob", "evaluation"),
    ),
)
def test_get_job_params_match(key, model_name, app_label, settings):
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
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
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
def test_transform_job_name(
    model, container, container_model, key, settings, mocker
):
    j = model(pk=uuid4(), time_limit=60)
    setattr(j, container, container_model(pk=uuid4()))
    # This test only exercises job-name transformation, which does not depend
    # on the task specs; the unsaved job has no inputs to build them from.
    mocker.patch.object(j, "inference_task_definitions", return_value=[])
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


@pytest.mark.django_db
def test_executor_task_specs_set_at_creation():
    job = AlgorithmJobFactory(
        time_limit=60,
        signing_key=b"totallysecret",
    )

    executor = job.get_executor(
        backend="grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor",
    )

    assert executor.total_task_time_limit == timedelta(seconds=60)


@pytest.mark.django_db
def test_execute_job_scheduled_job_with_time_limit(mocker):
    job = AlgorithmJobFactory(
        time_limit=60,
        signing_key=b"totallysecret",
        status=Job.PROVISIONED,
    )

    backend = "grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor"
    mocker.patch(
        "grandchallenge.components.models.ComponentImage.can_execute",
        new_callable=mocker.PropertyMock,
        return_value=True,
    )
    # Capture the time limit computed by the executor that execute_job builds
    create_job_boto = mocker.patch.object(
        AmazonSageMakerTrainingExecutor,
        "_create_job_boto",
        autospec=True,
    )

    execute_job(
        job_pk=job.pk,
        job_app_label=job._meta.app_label,
        job_model_name=job._meta.model_name,
        backend=backend,
    )

    create_job_boto.assert_called_once()
    scheduling_executor = create_job_boto.call_args.args[0]
    assert scheduling_executor.job_time_limit == timedelta(
        seconds=60
    ) + timedelta(seconds=settings.COMPONENTS_JOB_SETUP_DURATION)


@pytest.mark.django_db
def test_invocation_json(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN = (
        "arn:aws:iam::123456789012:role/service-role/ExecutionRole"
    )

    job = AlgorithmJobFactory(
        time_limit=60,
        signing_key=b"totallysecret",
    )
    job.algorithm_model = AlgorithmModelFactory()
    # This test asserts the invocation JSON shape for a job with no inputs;
    # clear the default input created by the factory.
    job.inputs.clear()

    executor = job.get_executor(
        backend="grandchallenge.components.backends.amazon_sagemaker_training.AmazonSageMakerTrainingExecutor",
    )

    with Stubber(executor._sagemaker_client) as s:
        s.add_response(
            method="create_training_job",
            service_response={"TrainingJobArn": "string"},
            expected_params={
                "TrainingJobName": executor._sagemaker_job_name,
                "AlgorithmSpecification": {
                    "TrainingInputMode": "File",
                    "TrainingImage": executor._exec_image_repo_tag,
                    "ContainerArguments": [
                        "invoke",
                        "--file",
                        f"s3://grand-challenge-components-inputs//invocations/algorithms/job/{job.pk}-00/invocation.json",
                    ],
                },
                "RoleArn": settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN,
                "OutputDataConfig": {
                    "S3OutputPath": f"s3://grand-challenge-components-outputs//training-outputs/algorithms/job/{job.pk}-00"
                },
                "ResourceConfig": {
                    "VolumeSizeInGB": 30,
                    "InstanceType": "ml.m7i.large",
                    "InstanceCount": 1,
                    "KeepAlivePeriodInSeconds": 0,
                },
                "StoppingCondition": {"MaxRuntimeInSeconds": 360},
                "Environment": {
                    "LOG_LEVEL": "INFO",
                    "PYTHONUNBUFFERED": "1",
                    "no_proxy": "amazonaws.com",
                    "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": "7168",
                    "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX": "746f74616c6c79736563726574",
                    "GRAND_CHALLENGE_COMPONENT_API_METHOD": "exec",
                    "GRAND_CHALLENGE_COMPONENT_MODEL": f"s3://grand-challenge-components-inputs//auxiliary-data/algorithms/job/{job.pk}-00/algorithm-model.tar.gz",
                    "GRAND_CHALLENGE_COMPONENT_RUNTIME_OUTPUT_BUCKET_NAME": "grand-challenge-components-outputs",
                    "GRAND_CHALLENGE_COMPONENT_RUNTIME_OUTPUT_PREFIX": f"/io/algorithms/job/{job.pk}-00",
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
        executor.provision()
        executor.execute()  # Required to validate expected_params in the stubber

    with io.BytesIO() as fileobj:
        executor._s3_client.download_fileobj(
            Fileobj=fileobj,
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=f"/invocations/algorithms/job/{job.pk}-00/invocation.json",
        )
        fileobj.seek(0)
        result = json.loads(fileobj.read().decode("utf-8"))

    assert executor._s3_client.head_object(
        Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
        Key=f"/auxiliary-data/algorithms/job/{job.pk}-00/algorithm-model.tar.gz",
    )

    assert result == [
        {
            "inputs": [
                {
                    "bucket_key": f"/io/algorithms/job/{job.pk}-00/inputs.json",
                    "bucket_name": "grand-challenge-components-inputs",
                    "decompress": False,
                    "relative_path": "inputs.json",
                },
            ],
            "output_bucket_name": "grand-challenge-components-outputs",
            "output_prefix": f"/io/algorithms/job/{job.pk}-00",
            "pk": f"algorithms-job-{job.pk}-00",
            "timeout": "PT1M",
        }
    ]


def test_set_utilization_duration():
    executor = AmazonSageMakerTrainingExecutor(
        job_id="algorithms-job-0",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
    )

    assert executor.utilization_duration is None

    executor._set_utilization_duration(
        event={
            "CreationTime": 1654683838000,
            "TrainingStartTime": 1654684027000,
            "TrainingEndTime": 1654684048000,
        }
    )

    assert executor.utilization_duration == timedelta(seconds=21)


def test_get_log_stream_name(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    logs_service = AmazonSageMakerTrainingLogsService(
        job_id=f"algorithms-job-{pk}",
    )

    with Stubber(logs_service._logs_client) as s:
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
        log_stream_name = logs_service._log_stream_name

    assert log_stream_name == f"localhost-A-{pk}/i-whatever"


def test_set_task_logs(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    logs_service = AmazonSageMakerTrainingLogsService(
        job_id=f"algorithms-job-{pk}",
    )

    with (
        Stubber(logs_service._sagemaker_client) as sagemaker,
        Stubber(logs_service._logs_client) as logs,
    ):
        sagemaker.add_response(
            method="describe_training_job",
            service_response={
                "TrainingJobName": f"localhost-A-{pk}",
                "TrainingJobArn": "",
                "ModelArtifacts": {"S3ModelArtifacts": ""},
                "TrainingJobStatus": "",
                "SecondaryStatus": "",
                "AlgorithmSpecification": {"TrainingInputMode": ""},
                "ResourceConfig": {"VolumeSizeInGB": 20},
                "StoppingCondition": {},
                "CreationTime": now().isoformat(),
                "TrainingStartTime": datetime(
                    2022, 6, 9, 9, 38, 47, tzinfo=timezone.utc
                ),
                "TrainingEndTime": datetime(
                    2022, 6, 9, 9, 37, 1, tzinfo=timezone.utc
                ),
            },
            expected_params={
                "TrainingJobName": f"localhost-A-{pk}",
            },
        )
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
                ],
                "nextBackwardToken": "foo",
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "startFromHead": False,
                "startTime": 1654767467000,
                "endTime": 1654767481000,
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={
                "events": [
                    {
                        "message": json.dumps(
                            {
                                "log": "first message",
                                "source": "stdout",
                                "internal": False,
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                ],
                "nextBackwardToken": "foo",
            },
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "startFromHead": False,
                "startTime": 1654767467000,
                "endTime": 1654767481000,
                "nextToken": "foo",
            },
        )

        assert logs_service.task_logs == [
            (
                datetime(2022, 6, 8, 10, 23, 58, tzinfo=timezone.utc),
                ParsedLog(
                    message="first message", source=SourceChoices.STDOUT
                ),
            ),
            (
                datetime(2022, 6, 8, 10, 23, 58, tzinfo=timezone.utc),
                ParsedLog(
                    message="hello from stdout", source=SourceChoices.STDOUT
                ),
            ),
            (
                datetime(2022, 6, 8, 10, 23, 58, tzinfo=timezone.utc),
                ParsedLog(
                    message="hello from stderr", source=SourceChoices.STDERR
                ),
            ),
        ]


def test_set_runtime_metrics(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    logs_service = AmazonSageMakerTrainingLogsService(
        job_id=f"algorithms-job-{pk}",
    )

    with (
        Stubber(logs_service._cloudwatch_client) as cloudwatch,
        Stubber(logs_service._sagemaker_client) as sagemaker,
    ):
        sagemaker.add_response(
            method="describe_training_job",
            service_response={
                "TrainingJobName": f"localhost-A-{pk}",
                "TrainingJobArn": "",
                "ModelArtifacts": {"S3ModelArtifacts": ""},
                "TrainingJobStatus": "",
                "SecondaryStatus": "",
                "AlgorithmSpecification": {"TrainingInputMode": ""},
                "ResourceConfig": {
                    "VolumeSizeInGB": 20,
                    "InstanceType": "ml.m7i.large",
                },
                "StoppingCondition": {},
                "CreationTime": now().isoformat(),
                "TrainingStartTime": datetime(
                    2022, 6, 9, 9, 37, 47, tzinfo=timezone.utc
                ),
                "TrainingEndTime": datetime(
                    2022, 6, 9, 9, 42, 1, tzinfo=timezone.utc
                ),
            },
            expected_params={
                "TrainingJobName": f"localhost-A-{pk}",
            },
        )
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

        assert logs_service._runtime_metrics == {
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


def test_handle_completed_job(settings):
    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"itsasecret",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[ComponentInterfaceValueFactory.build()],
                time_limit=timedelta(seconds=100),
            )
        ],
    )

    runtime_setup_result = RuntimeSetupResult(
        return_code=0,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )
    inference_result = InferenceResult(
        pk=f"algorithms-job-{pk}",
        return_code=0,
        user_safe_error_message="",
        user_process_last_stderr_lines=[],
        exec_duration=timedelta(seconds=51432),
        invoke_duration=timedelta(seconds=1543),
        outputs=[],
        sagemaker_shim_version="0.5.0",
    )
    inference_result_content = inference_result.model_dump_json().encode(
        "utf-8"
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=inference_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(inference_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor._get_inference_result_key(),
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    assert executor._handle_completed_job() is None

    assert executor.inference_results[0].exec_duration == timedelta(
        seconds=51432
    )
    assert executor.inference_results[0].invoke_duration == timedelta(
        seconds=1543
    )


def test_handle_completed_job_with_runtime_setup_failed(settings):
    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"itsasecret",
        api_method=APIMethodChoices.INVOKE,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[ComponentInterfaceValueFactory.build()],
                time_limit=timedelta(seconds=100),
            )
        ],
    )
    runtime_setup_result = RuntimeSetupResult(
        return_code=1,
        user_safe_error_message="setup failed",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    with pytest.raises(ComponentException, match="setup failed"):
        executor._handle_completed_job()


def test_handle_completed_job_missing_runtime_setup_result():
    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"itsasecret",
        api_method=APIMethodChoices.INVOKE,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[ComponentInterfaceValueFactory.build()],
                time_limit=timedelta(seconds=100),
            )
        ],
    )

    with pytest.raises(UncleanExit):
        executor._handle_completed_job()


def test_handle_completed_job_missing_inference_result(settings):
    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"itsasecret",
        api_method=APIMethodChoices.INVOKE,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[ComponentInterfaceValueFactory.build()],
                time_limit=timedelta(seconds=100),
            )
        ],
    )
    runtime_setup_result = RuntimeSetupResult(
        return_code=0,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    runtime_setup_result_content = (
        runtime_setup_result.model_dump_json().encode("utf-8")
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=runtime_setup_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=executor.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    with pytest.raises(ComponentException) as error:
        executor._handle_completed_job()

    assert str(error.value) == SystemErrorMessages.UNEXPECTED_ERROR


def test_handle_time_limit_exceeded(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
    )

    with pytest.raises(ComponentException) as error:
        executor._handle_stopped_job(
            event={
                "TrainingJobStatus": "Stopped",
                "SecondaryStatus": "MaxRuntimeExceeded",
            }
        )

    assert SystemErrorMessages.TIME_LIMIT_EXCEEDED in str(error)


def test_handle_stopped_event(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
        task_definitions=[
            InferenceTaskDefinition(
                input_civs=[ComponentInterfaceValueFactory.build()],
                time_limit=timedelta(seconds=100),
            )
        ],
    )

    with (
        Stubber(executor._logs_client) as logs,
        Stubber(executor._cloudwatch_client) as cloudwatch,
    ):
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
            service_response={"events": [], "nextBackwardToken": "foo"},
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "startFromHead": False,
                "startTime": 1654767467000,
                "endTime": 1654767481000,
            },
        )
        logs.add_response(
            method="get_log_events",
            service_response={"events": [], "nextBackwardToken": "foo"},
            expected_params={
                "logGroupName": "/aws/sagemaker/TrainingJobs",
                "logStreamName": f"localhost-A-{pk}/i-whatever",
                "startFromHead": False,
                "startTime": 1654767467000,
                "endTime": 1654767481000,
                "nextToken": "foo",
            },
        )

        with pytest.raises(TaskCancelled):
            executor.handle_event(
                event={
                    "TrainingJobStatus": "Stopped",
                    "SecondaryStatus": "Stopped",
                    "TrainingStartTime": 1654767467000,
                    "TrainingEndTime": 1654767481000,
                    "ResourceConfig": {
                        "InstanceType": "ml.m7i.large",
                        "InstanceCount": 1,
                    },
                }
            )


def test_deprovision(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"

    pk = uuid4()
    executor = AmazonSageMakerTrainingExecutor(
        job_id=f"algorithms-job-{pk}",
        exec_image_repo_tag="",
        memory_limit=4,
        requires_gpu_type=GPUTypeChoices.NO_GPU,
        use_warm_pool=False,
        signing_key=b"",
        api_method=APIMethodChoices.EXEC,
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


def _upload_signed(*, executor, key, content):
    signature = hmac.new(
        key=executor._signing_key,
        msg=content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    executor._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(content),
        Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        Key=key,
        ExtraArgs={"Metadata": {"signature_hmac_sha256": signature}},
    )


def _write_runtime_setup_result(*, executor, return_code=0):
    result = RuntimeSetupResult(
        return_code=return_code,
        user_safe_error_message="",
        sagemaker_shim_version="0.8.0",
    )
    _upload_signed(
        executor=executor,
        key=executor.runtime_setup_result_key,
        content=result.model_dump_json().encode("utf-8"),
    )


def _write_task_inference_result(
    *,
    executor,
    output_prefix,
    pk,
    return_code=0,
    exec_duration=None,
    invoke_duration=None,
    user_safe_error_message="",
):
    result = InferenceResult(
        pk=pk,
        return_code=return_code,
        user_safe_error_message=user_safe_error_message,
        user_process_last_stderr_lines=[],
        exec_duration=exec_duration,
        invoke_duration=invoke_duration,
        outputs=[],
        sagemaker_shim_version="0.8.0",
    )
    _upload_signed(
        executor=executor,
        key=safe_join(
            output_prefix, ".sagemaker_shim", "inference_result.json"
        ),
        content=result.model_dump_json().encode("utf-8"),
    )


@pytest.mark.django_db
def test_handle_event_for_batchjob():
    batch_job = BatchJobFactory(
        input_civ_sets=[
            {ComponentInterfaceValueFactory()},
            {ComponentInterfaceValueFactory()},
        ],
        time_limit=10,
    )
    first_task, second_task = batch_job.tasks.all()

    executor = AmazonSageMakerTrainingExecutor(**batch_job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    for task, exec_seconds, invoke_seconds in (
        (first_task, 10, 20),
        (second_task, 30, 40),
    ):
        _write_task_inference_result(
            executor=executor,
            output_prefix=executor._get_output_prefix_for_task(
                task_pk=str(task.pk)
            ),
            pk=f"{executor._job_id}-{task.pk}",
            return_code=0,
            exec_duration=timedelta(seconds=exec_seconds),
            invoke_duration=timedelta(seconds=invoke_seconds),
        )

    executor.handle_event(
        event={
            "TrainingJobName": executor._sagemaker_job_name,
            "TrainingJobStatus": "Completed",
            "SecondaryStatus": "Completed",
            "TrainingStartTime": 1654767467000,
            "TrainingEndTime": 1654767481000,
        },
    )

    results_by_task_pk = {
        result.pk: result for result in executor.inference_results
    }
    assert set(results_by_task_pk) == {
        f"{executor._job_id}-{first_task.pk}",
        f"{executor._job_id}-{second_task.pk}",
    }

    first_result = results_by_task_pk[f"{executor._job_id}-{first_task.pk}"]
    assert first_result.return_code == 0
    assert first_result.user_safe_error_message == ""
    assert first_result.exec_duration == timedelta(seconds=10)
    assert first_result.invoke_duration == timedelta(seconds=20)

    second_result = results_by_task_pk[f"{executor._job_id}-{second_task.pk}"]
    assert second_result.exec_duration == timedelta(seconds=30)


@pytest.mark.django_db
def test_handle_event_for_batchjob_task_failure():
    batch_job = BatchJobFactory(
        input_civ_sets=[
            {ComponentInterfaceValueFactory()},
            {ComponentInterfaceValueFactory()},
        ],
        time_limit=10,
    )
    first_task, second_task = batch_job.tasks.all()

    executor = AmazonSageMakerTrainingExecutor(**batch_job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix_for_task(
            task_pk=str(first_task.pk)
        ),
        pk=f"{executor._job_id}-{first_task.pk}",
        return_code=0,
    )
    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix_for_task(
            task_pk=str(second_task.pk)
        ),
        pk=f"{executor._job_id}-{second_task.pk}",
        return_code=1,  # failed task
        user_safe_error_message="Something went wrong",
    )

    with pytest.raises(ComponentException):
        executor.handle_event(
            event={
                "TrainingJobName": executor._sagemaker_job_name,
                "TrainingJobStatus": "Completed",
                "SecondaryStatus": "Completed",
                "TrainingStartTime": 1654767467000,
                "TrainingEndTime": 1654767481000,
            },
        )

    return_codes = {
        result.return_code for result in executor.inference_results
    }
    assert return_codes == {0, 1}


TRAINING_BACKEND = (
    "grandchallenge.components.backends.amazon_sagemaker_training."
    "AmazonSageMakerTrainingExecutor"
)


@pytest.mark.django_db
def test_handle_event_task_for_batchjob(mocker):
    batch_job = BatchJobFactory(
        status=BatchJob.EXECUTING,
        input_civ_sets=[
            {ComponentInterfaceValueFactory()},
            {ComponentInterfaceValueFactory()},
        ],
        time_limit=10,
    )
    first_task, second_task = batch_job.tasks.all()

    executor = AmazonSageMakerTrainingExecutor(**batch_job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    for task, exec_seconds, invoke_seconds in (
        (first_task, 10, 20),
        (second_task, 30, 40),
    ):
        _write_task_inference_result(
            executor=executor,
            output_prefix=executor._get_output_prefix_for_task(
                task_pk=str(task.pk)
            ),
            pk=f"{executor._job_id}-{task.pk}",
            return_code=0,
            exec_duration=timedelta(seconds=exec_seconds),
            invoke_duration=timedelta(seconds=invoke_seconds),
        )

    schedule_parse_output = mocker.patch(
        "grandchallenge.components.tasks.parse_job_output.execute_on_commit",
    )

    handle_event(
        event={
            "TrainingJobName": executor._sagemaker_job_name,
            "TrainingJobStatus": "Completed",
            "SecondaryStatus": "Completed",
            "TrainingStartTime": 1654767467000,
            "TrainingEndTime": 1654767481000,
        },
        backend=TRAINING_BACKEND,
    )

    batch_job.refresh_from_db()
    assert batch_job.status == BatchJob.PARSING

    first_task.refresh_from_db()
    assert first_task.exec_duration == timedelta(seconds=10)
    assert first_task.invoke_duration == timedelta(seconds=20)

    second_task.refresh_from_db()
    assert second_task.exec_duration == timedelta(seconds=30)
    assert second_task.invoke_duration == timedelta(seconds=40)

    assert schedule_parse_output.call_count == 2
    scheduled_task_pks = {
        call.kwargs["task_pk"] for call in schedule_parse_output.call_args_list
    }
    assert scheduled_task_pks == {str(first_task.pk), str(second_task.pk)}


@pytest.mark.django_db
def test_handle_event_task_for_batchjob_task_failure(mocker):
    batch_job = BatchJobFactory(
        status=BatchJob.EXECUTING,
        input_civ_sets=[
            {ComponentInterfaceValueFactory()},
            {ComponentInterfaceValueFactory()},
        ],
        time_limit=10,
    )
    first_task, second_task = batch_job.tasks.all()

    executor = AmazonSageMakerTrainingExecutor(**batch_job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix_for_task(
            task_pk=str(first_task.pk)
        ),
        pk=f"{executor._job_id}-{first_task.pk}",
        return_code=0,
        exec_duration=timedelta(seconds=10),
        invoke_duration=timedelta(seconds=20),
    )
    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix_for_task(
            task_pk=str(second_task.pk)
        ),
        pk=f"{executor._job_id}-{second_task.pk}",
        return_code=1,  # failed task
        exec_duration=timedelta(seconds=30),
        invoke_duration=timedelta(seconds=40),
        user_safe_error_message="Something went wrong",
    )

    schedule_parse_output = mocker.patch(
        "grandchallenge.components.tasks.parse_job_output.execute_on_commit",
    )

    handle_event(
        event={
            "TrainingJobName": executor._sagemaker_job_name,
            "TrainingJobStatus": "Completed",
            "SecondaryStatus": "Completed",
            "TrainingStartTime": 1654767467000,
            "TrainingEndTime": 1654767481000,
        },
        backend=TRAINING_BACKEND,
    )

    batch_job.refresh_from_db()
    assert batch_job.status == BatchJob.FAILURE
    assert batch_job.error_message == "Something went wrong"

    # durations are logged for both the successful and failed tasks
    first_task.refresh_from_db()
    assert first_task.exec_duration == timedelta(seconds=10)
    assert first_task.invoke_duration == timedelta(seconds=20)

    second_task.refresh_from_db()
    assert second_task.exec_duration == timedelta(seconds=30)
    assert second_task.invoke_duration == timedelta(seconds=40)

    # no output parsing is scheduled.
    schedule_parse_output.assert_not_called()


@pytest.mark.django_db
def test_handle_event_task_for_job(django_capture_on_commit_callbacks):
    job = AlgorithmJobFactory(
        status=Job.EXECUTING,
        signing_key=b"itsasecret",
        time_limit=60,
    )

    executor = AmazonSageMakerTrainingExecutor(**job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix(),
        pk=executor._job_id,
        return_code=0,
        exec_duration=timedelta(seconds=10),
        invoke_duration=timedelta(seconds=20),
    )

    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        handle_event(
            event={
                "TrainingJobName": executor._sagemaker_job_name,
                "TrainingJobStatus": "Completed",
                "SecondaryStatus": "Completed",
                "TrainingStartTime": 1654767467000,
                "TrainingEndTime": 1654767481000,
            },
            backend=TRAINING_BACKEND,
        )

    job.refresh_from_db()
    assert job.status == Job.PARSING
    assert job.exec_duration == timedelta(seconds=10)
    assert job.invoke_duration == timedelta(seconds=20)
    # 1654767481000 - 1654767467000 == 14 seconds
    assert job.utilization.duration == timedelta(seconds=14)
    # Output parsing is scheduled once per output interface.
    assert len(callbacks) == job.output_interfaces.count()


@pytest.mark.django_db
def test_handle_event_task_for_job_failure(
    django_capture_on_commit_callbacks, settings
):
    job = AlgorithmJobFactory(
        status=Job.EXECUTING,
        signing_key=b"itsasecret",
        time_limit=60,
    )

    executor = AmazonSageMakerTrainingExecutor(**job.executor_kwargs)

    _write_runtime_setup_result(executor=executor)

    _write_task_inference_result(
        executor=executor,
        output_prefix=executor._get_output_prefix(),
        pk=executor._job_id,
        return_code=1,  # failed
        exec_duration=timedelta(seconds=10),
        invoke_duration=timedelta(seconds=20),
        user_safe_error_message="Something went wrong",
    )

    with django_capture_on_commit_callbacks(execute=False):
        handle_event(
            event={
                "TrainingJobName": executor._sagemaker_job_name,
                "TrainingJobStatus": "Completed",
                "SecondaryStatus": "Completed",
                "TrainingStartTime": 1654767467000,
                "TrainingEndTime": 1654767481000,
            },
            backend=TRAINING_BACKEND,
        )

    job.refresh_from_db()
    assert job.status == Job.FAILURE
    assert job.error_message == "Something went wrong"
    assert job.exec_duration == timedelta(seconds=10)
    assert job.invoke_duration == timedelta(seconds=20)
    assert job.utilization.duration == timedelta(seconds=14)
