import hashlib
import hmac
import io
import json
from datetime import timedelta
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
    EndpointOrchestrator,
)
from grandchallenge.components.backends.base import (
    InferenceResult,
    RuntimeSetupResult,
    s3_upload_content,
)
from grandchallenge.components.models import InterfaceKindChoices
from grandchallenge.components.schemas import GPUTypeChoices
from tests.algorithms_tests.factories import EndpointFactory, InvocationFactory
from tests.components_tests.factories import (
    ComponentInterfaceFactory,
    ComponentInterfaceValueFactory,
)


class TestEndpointOrchestratorProperties:
    def test_algorithm_model_key(self):
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._algorithm_model_key == (
            f"/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz"
        )

    def test_algorithm_model_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._algorithm_model_s3_uri == (
            f"s3://algorithm-endpoints-input//auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz"
        )

    def test_output_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME = (
            "algorithm-endpoints-output"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._output_s3_uri == (
            f"s3://algorithm-endpoints-output//io/algorithms/endpoint/{endpoint.pk}/successes"
        )

    def test_failure_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME = (
            "algorithm-endpoints-output"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._failure_s3_uri == (
            f"s3://algorithm-endpoints-output//io/algorithms/endpoint/{endpoint.pk}/failures"
        )

    def test_invocation_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        invocation = InvocationFactory.build()
        orchestrator = invocation.orchestrator

        assert orchestrator._invocation_s3_uri == (
            f"s3://algorithm-endpoints-input//invocations/algorithms/invocation/{invocation.pk}/invocation.json"
        )

    def test_endpoint_invocation_environment(self, settings):
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME = (
            "algorithm-endpoints-output"
        )
        endpoint = EndpointFactory.build(
            signing_key=b"totallysecret",
        )
        orchestrator = endpoint.orchestrator

        assert orchestrator.invocation_environment == {
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "no_proxy": "amazonaws.com",
            "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": "7168",
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX": "746f74616c6c79736563726574",
            "GRAND_CHALLENGE_COMPONENT_API_METHOD": endpoint.algorithm_image.api_method,
            "GRAND_CHALLENGE_COMPONENT_MODEL": f"s3://algorithm-endpoints-input//auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz",
            "GRAND_CHALLENGE_COMPONENT_RUNTIME_OUTPUT_BUCKET_NAME": "algorithm-endpoints-output",
            "GRAND_CHALLENGE_COMPONENT_RUNTIME_OUTPUT_PREFIX": f"/io/algorithms/endpoint/{endpoint.pk}",
        }

        orchestrator = EndpointFactory.build(algorithm_model=None).orchestrator

        assert (
            "GRAND_CHALLENGE_COMPONENT_MODEL"
            not in orchestrator.invocation_environment
        )

    def test_required_volume_size_gb(self):
        orchestrator = EndpointFactory.build(
            requires_gpu_type=GPUTypeChoices.NO_GPU,
        ).orchestrator

        assert orchestrator._instance_type.nvme_volume_size is None
        assert orchestrator._required_volume_size_gb == 30

        orchestrator = EndpointFactory.build(
            requires_gpu_type=GPUTypeChoices.T4,
        ).orchestrator

        assert orchestrator._instance_type.nvme_volume_size is not None
        assert (
            orchestrator._required_volume_size_gb
            == orchestrator._instance_type.nvme_volume_size
        )

    def test_buckets_names_on_executor(self, settings):
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME = (
            "algorithm-endpoints-output"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert (
            orchestrator._executor._input_bucket_name
            == "algorithm-endpoints-input"
        )
        assert (
            orchestrator._executor._output_bucket_name
            == "algorithm-endpoints-output"
        )

    def test_runtime_setup_result_key(self):
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator.runtime_setup_result_key == (
            f"/io/algorithms/endpoint/{endpoint.pk}/.sagemaker_shim/runtime_setup_result.json"
        )

    def test_runtime_setup_result_key_invocation(self):
        invocation = InvocationFactory.build()
        endpoint = invocation.endpoint
        orchestrator = invocation.orchestrator

        assert (
            orchestrator.runtime_setup_result_key
            == endpoint.orchestrator.runtime_setup_result_key
            == (
                f"/io/algorithms/endpoint/{endpoint.pk}/.sagemaker_shim/runtime_setup_result.json"
            )
        )


def test_endpoint_provision_auxiliary_data(settings):
    settings.PROTECTED_S3_STORAGE_KWARGS = {
        "bucket_name": "from_protected_storage"
    }
    settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = "to_endpoint_input"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._s3_client) as stubber:
        stubber.add_response(
            method="head_object",
            service_response={"ContentLength": 3},
            expected_params={
                "Bucket": "from_protected_storage",
                "Key": str(endpoint.algorithm_model.model),
            },
        )
        stubber.add_response(
            method="copy_object",
            service_response={},
            expected_params={
                "CopySource": {
                    "Bucket": "from_protected_storage",
                    "Key": str(endpoint.algorithm_model.model),
                },
                "Bucket": "to_endpoint_input",
                "Key": orchestrator._algorithm_model_key,
            },
        )

        orchestrator.provision_auxiliary_data()

        stubber.assert_no_pending_responses()


def test_endpoint_deprovision_auxiliary_data(settings):
    settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = "endpoint_io"
    orchestrator = EndpointFactory.build().orchestrator

    with Stubber(orchestrator._s3_client) as stubber:
        stubber.add_response(
            method="list_objects_v2",
            service_response={},
            expected_params={
                "Bucket": "endpoint_io",
                "Prefix": orchestrator._auxiliary_data_prefix,
            },
        )

        orchestrator.deprovision_auxiliary_data()

        stubber.assert_no_pending_responses()


def test_endpoint_create_sagemaker_model(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    settings.ALGORITHM_ENDPOINTS_EXECUTION_ROLE_ARN = "test_execution_role_arn"
    settings.ALGORITHM_ENDPOINTS_SECURITY_GROUP_ID = "test_security_group_id"
    settings.ALGORITHM_ENDPOINTS_SUBNETS = ["test_subnet1", "test_subnet2"]
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="create_model",
            service_response={"ModelArn": "some_model_arn_for_testing"},
            expected_params={
                "ModelName": endpoint.endpoint_name,
                "ExecutionRoleArn": "test_execution_role_arn",
                "PrimaryContainer": {
                    "Image": str(endpoint.algorithm_image.shimmed_repo_tag),
                    "Environment": orchestrator.invocation_environment,
                    "Mode": "SingleModel",
                },
                "VpcConfig": {
                    "SecurityGroupIds": ["test_security_group_id"],
                    "Subnets": ["test_subnet1", "test_subnet2"],
                },
            },
        )

        orchestrator.create_sagemaker_model()

        stubber.assert_no_pending_responses()


def test_endpoint_delete_sagemaker_model(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="delete_model",
            service_response={},
            expected_params={
                "ModelName": endpoint.endpoint_name,
            },
        )

        orchestrator.delete_sagemaker_model()

        stubber.assert_no_pending_responses()


def test_endpoint_create_endpoint_config(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    settings.ALGORITHM_ENDPOINTS_SNS_TOPIC_ARN = "some_sns_arn"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="create_endpoint_config",
            service_response={"EndpointConfigArn": "some_endpoint_config_arn"},
            expected_params={
                "EndpointConfigName": endpoint.endpoint_name,
                "AsyncInferenceConfig": {
                    "ClientConfig": {
                        "MaxConcurrentInvocationsPerInstance": 1,
                    },
                    "OutputConfig": {
                        "S3FailurePath": orchestrator._failure_s3_uri,
                        "S3OutputPath": orchestrator._output_s3_uri,
                        "NotificationConfig": {
                            "SuccessTopic": settings.ALGORITHM_ENDPOINTS_SNS_TOPIC_ARN,
                            "ErrorTopic": settings.ALGORITHM_ENDPOINTS_SNS_TOPIC_ARN,
                        },
                    },
                },
                "ProductionVariants": [
                    {
                        "VariantName": endpoint.endpoint_name,
                        "ContainerStartupHealthCheckTimeoutInSeconds": 300,
                        "InitialInstanceCount": 1,
                        "InitialVariantWeight": 1,
                        "InstanceType": orchestrator._instance_type.name,
                        "ModelName": endpoint.endpoint_name,
                        "VolumeSizeInGB": orchestrator._required_volume_size_gb,
                    }
                ],
            },
        )

        orchestrator.create_endpoint_config()

        stubber.assert_no_pending_responses()


def test_endpoint_delete_endpoint_config(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="delete_endpoint_config",
            service_response={},
            expected_params={
                "EndpointConfigName": endpoint.endpoint_name,
            },
        )

        orchestrator.delete_endpoint_config()

        stubber.assert_no_pending_responses()


def test_endpoint_create_endpoint(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="create_endpoint",
            service_response={"EndpointArn": "some_endpoint_arn_for_test"},
            expected_params={
                "EndpointName": endpoint.endpoint_name,
                "EndpointConfigName": endpoint.endpoint_name,
            },
        )

        orchestrator.create_endpoint()

        stubber.assert_no_pending_responses()


def test_endpoint_delete_endpoint(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    endpoint = EndpointFactory.build()
    orchestrator = endpoint.orchestrator

    with Stubber(orchestrator._sagemaker_client) as stubber:
        stubber.add_response(
            method="delete_endpoint",
            service_response={},
            expected_params={
                "EndpointName": endpoint.endpoint_name,
            },
        )

        orchestrator.delete_endpoint()

        stubber.assert_no_pending_responses()


deprovision_endpoint_method_names = [
    "delete_endpoint",
    "delete_endpoint_config",
    "delete_sagemaker_model",
    "deprovision_auxiliary_data",
]


def test_endpoint_orchestrator_deprovision(mocker):
    orchestrator = EndpointFactory.build().orchestrator

    mock_deprovision_methods = [
        mocker.patch.object(
            EndpointOrchestrator,
            method_name,
        )
        for method_name in deprovision_endpoint_method_names
    ]

    orchestrator.deprovision()

    for mock_method in mock_deprovision_methods:
        mock_method.assert_called_once()


@pytest.mark.parametrize(
    "method_with_error", deprovision_endpoint_method_names
)
def test_endpoint_orchestrator_deprovision_errors(mocker, method_with_error):
    orchestrator = EndpointFactory.build().orchestrator
    for method_name in deprovision_endpoint_method_names:
        if method_name == method_with_error:
            kwargs = {"side_effect": Exception("test error")}
        else:
            kwargs = {}
        mocker.patch.object(
            EndpointOrchestrator,
            method_name,
            **kwargs,
        )

    # assert error is not ignored
    with pytest.raises(Exception, match="test error"):
        orchestrator.deprovision()


def test_endpoint_orchestrator_deprovision_ignored_errors(mocker):
    orchestrator = EndpointFactory.build().orchestrator

    mock_deprovision_methods = [
        mocker.patch.object(
            EndpointOrchestrator,
            "delete_endpoint",
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": 'Could not find endpoint "foobar".',
                    }
                },
                "DeleteEndpoint",
            ),
        ),
        mocker.patch.object(
            EndpointOrchestrator,
            "delete_endpoint_config",
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": 'Could not find endpoint configuration "foobar".',
                    }
                },
                "DeleteEndpointConfig",
            ),
        ),
        mocker.patch.object(
            EndpointOrchestrator,
            "delete_sagemaker_model",
            side_effect=ClientError(
                {
                    "Error": {
                        "Code": "ValidationException",
                        "Message": 'Could not find model "foobar".',
                    }
                },
                "DeleteModel",
            ),
        ),
        mocker.patch.object(
            EndpointOrchestrator,
            "deprovision_auxiliary_data",
        ),
    ]

    orchestrator.deprovision()

    # assert all called
    for mock_method in mock_deprovision_methods:
        mock_method.assert_called_once()


def test_endpoint_orchestrator_auxiliary_data_tasks_empty():
    orchestrator = InvocationFactory.build().orchestrator

    assert orchestrator._executor._auxiliary_data_provisioning_tasks == []


@pytest.mark.django_db
def test_endpoint_orchestrator_provision_invocation_input_data_tasks(
    mocker, settings
):
    settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
        "algorithm-endpoints-input"
    )
    settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME = (
        "algorithm-endpoints-output"
    )
    invocation = InvocationFactory(time_limit=42)
    ci = ComponentInterfaceFactory(kind=InterfaceKindChoices.INTEGER)
    civ = ComponentInterfaceValueFactory(interface=ci, value=42)
    invocation.inputs.add(civ)
    orchestrator = invocation.orchestrator

    expected_inputs_json = [
        {
            "value": 42,
            "file": None,
            "pk": civ.pk,
            "image": None,
            "interface": {
                "kind": "Integer",
                "super_kind": "Value",
                "look_up_table": None,
                "title": ci.title,
                "description": "",
                "slug": ci.slug,
                "pk": ci.pk,
                "default_value": None,
                "relative_path": ci.relative_path,
                "overlay_segments": [],
            },
            "socket": {
                "kind": "Integer",
                "super_kind": "Value",
                "look_up_table": None,
                "title": ci.title,
                "description": "",
                "slug": ci.slug,
                "pk": ci.pk,
                "default_value": None,
                "relative_path": ci.relative_path,
                "overlay_segments": [],
            },
        },
    ]
    expected_invocation_json = {
        "pk": f"algorithms-invocation-{invocation.pk}",
        "inputs": [
            {
                "relative_path": f"{ci.relative_path}",
                "bucket_name": "algorithm-endpoints-input",
                "bucket_key": f"/io/algorithms/invocation/{invocation.pk}/{ci.relative_path}",
                "decompress": False,
            },
            {
                "relative_path": "inputs.json",
                "bucket_name": "algorithm-endpoints-input",
                "bucket_key": f"/io/algorithms/invocation/{invocation.pk}/inputs.json",
                "decompress": False,
            },
        ],
        "output_bucket_name": "algorithm-endpoints-output",
        "output_prefix": f"/io/algorithms/invocation/{invocation.pk}",
        "timeout": "PT42S",
    }

    mock_provision = mocker.patch.object(orchestrator._executor, "_provision")

    orchestrator.provision_invocation_input_data(input_civs=[civ])

    mock_provision.assert_called_once()

    mock_call = mock_provision.mock_calls[0]
    _, _, mock_call_kwargs = mock_call
    provisioning_tasks = mock_call_kwargs["tasks"]

    assert len(provisioning_tasks) == 3

    copy_civ_task = provisioning_tasks[0]
    upload_inputs_json_task = provisioning_tasks[1]
    create_invocation_json_task = provisioning_tasks[2]

    assert copy_civ_task.func == s3_upload_content
    assert copy_civ_task.keywords["bucket"] == "algorithm-endpoints-input"
    assert (
        copy_civ_task.keywords["key"]
        == f"/io/algorithms/invocation/{invocation.pk}/{ci.relative_path}"
    )
    assert copy_civ_task.keywords["content"] == b"42"

    assert upload_inputs_json_task.func == s3_upload_content
    assert (
        upload_inputs_json_task.keywords["bucket"]
        == "algorithm-endpoints-input"
    )
    assert (
        upload_inputs_json_task.keywords["key"]
        == f"/io/algorithms/invocation/{invocation.pk}/inputs.json"
    )

    inputs_json = json.loads(upload_inputs_json_task.keywords["content"])

    assert inputs_json == expected_inputs_json

    assert create_invocation_json_task.func == s3_upload_content
    assert (
        create_invocation_json_task.keywords["bucket"]
        == "algorithm-endpoints-input"
    )
    assert (
        create_invocation_json_task.keywords["key"]
        == f"/invocations/algorithms/invocation/{invocation.pk}/invocation.json"
    )

    invocation_json = json.loads(
        create_invocation_json_task.keywords["content"]
    )

    assert invocation_json == expected_invocation_json


def test_invocation_invoke_endpoint(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    invocation = InvocationFactory.build(time_limit=42)
    orchestrator = invocation.orchestrator

    with Stubber(orchestrator._sagemaker_runtime_client) as stubber:
        stubber.add_response(
            method="invoke_endpoint_async",
            service_response={"InferenceId": invocation.inference_id},
            expected_params={
                "EndpointName": invocation.endpoint.endpoint_name,
                "ContentType": "application/json",
                "InputLocation": orchestrator._invocation_s3_uri,
                "InferenceId": invocation.inference_id,
                "InvocationTimeoutSeconds": 42,
            },
        )

        orchestrator.invoke_endpoint(inference_id=invocation.inference_id)

        stubber.assert_no_pending_responses()


def test_get_invocation_params_match(settings):
    pk = uuid4()
    event = {"inferenceId": f"{settings.COMPONENTS_REGISTRY_PREFIX}-AEI-{pk}"}
    inference_id = EndpointOrchestrator.get_inference_id(event=event)
    invocation_params = EndpointOrchestrator.get_invocation_params(
        inference_id=inference_id
    )

    assert invocation_params.pk == str(pk)
    assert invocation_params.model_name == "invocation"
    assert invocation_params.app_label == "algorithms"


def test_handle_completed_invocation(settings):
    invocation = InvocationFactory.build(endpoint__signing_key=b"itsasecret")
    orchestrator = invocation.orchestrator
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
    orchestrator._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(runtime_setup_result_content),
        Bucket=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        Key=orchestrator.runtime_setup_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )
    inference_result = InferenceResult(
        pk=f"algorithms-invocation-{invocation.pk}",
        return_code=0,
        user_safe_error_message="",
        user_process_last_stderr_lines=[],
        exec_duration=None,
        invoke_duration=timedelta(seconds=12),
        outputs=[],
        sagemaker_shim_version="0.7.0",
    )
    inference_result_content = inference_result.model_dump_json().encode(
        "utf-8"
    )
    signature = hmac.new(
        key=b"itsasecret",
        msg=inference_result_content,
        digestmod=hashlib.sha256,
    ).hexdigest()
    orchestrator._s3_client.upload_fileobj(
        Fileobj=io.BytesIO(inference_result_content),
        Bucket=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        Key=orchestrator._executor._inference_result_key,
        ExtraArgs={
            "Metadata": {"signature_hmac_sha256": signature},
        },
    )

    assert orchestrator.invoke_duration is None

    orchestrator._handle_completed_invocation()

    assert orchestrator.invoke_duration == timedelta(seconds=12)


def test_set_invocation_logs(settings):
    settings.COMPONENTS_AMAZON_ECR_REGION = "us-east-1"
    settings.COMPONENTS_REGISTRY_PREFIX = "localhost"

    invocation = InvocationFactory.build()
    orchestrator = invocation.orchestrator
    endpoint = invocation.endpoint

    assert orchestrator.stdout == ""
    assert orchestrator.stderr == ""

    with Stubber(orchestrator._executor._logs_client) as logs:
        logs.add_response(
            method="describe_log_streams",
            service_response={
                "logStreams": [
                    {
                        "logStreamName": f"localhost-AE-{endpoint.pk}/i-whatever"
                    },
                ]
            },
            expected_params={
                "logGroupName": f"/aws/sagemaker/Endpoints/localhost-AE-{endpoint.pk}",
                "logStreamNamePrefix": f"localhost-AE-{endpoint.pk}",
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
                                "task": f"algorithms-invocation-{invocation.pk}",
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
                                "task": f"algorithms-invocation-{invocation.pk}",
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "endpoint stderr",
                                "source": "stderr",
                                "internal": False,
                                "task": f"algorithms-endpoint-{endpoint.pk}",
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                    {
                        "message": json.dumps(
                            {
                                "log": "endpoint stdout",
                                "source": "stdout",
                                "internal": False,
                                "task": f"algorithms-endpoint-{endpoint.pk}",
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
                                "task": f"algorithms-invocation-{invocation.pk}",
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
                                "task": f"algorithms-invocation-{invocation.pk}",
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
                "logGroupName": f"/aws/sagemaker/Endpoints/localhost-AE-{endpoint.pk}",
                "logStreamName": f"localhost-AE-{endpoint.pk}/i-whatever",
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
                                "task": f"algorithms-invocation-{invocation.pk}",
                            }
                        ),
                        "timestamp": 1654683838000,
                    },
                ],
                "nextBackwardToken": "foo",
            },
            expected_params={
                "logGroupName": f"/aws/sagemaker/Endpoints/localhost-AE-{endpoint.pk}",
                "logStreamName": f"localhost-AE-{endpoint.pk}/i-whatever",
                "startFromHead": False,
                "startTime": 1654767467000,
                "endTime": 1654767481000,
                "nextToken": "foo",
            },
        )
        orchestrator.set_task_logs(
            event={
                "receivedTime": "2022-06-09T09:37:47.000Z",
                "eventTime": "2022-06-09T09:37:51.000Z",
            },
        )

    assert (
        orchestrator.stdout
        == "2022-06-08T10:23:58+00:00 first message\n2022-06-08T10:23:58+00:00 hello from stdout"
    )
    assert orchestrator.stderr == "2022-06-08T10:23:58+00:00 hello from stderr"
