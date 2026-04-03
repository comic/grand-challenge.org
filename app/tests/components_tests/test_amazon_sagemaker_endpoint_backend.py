import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
    EndpointOrchestrator,
)
from grandchallenge.components.schemas import GPUTypeChoices
from tests.algorithms_tests.factories import EndpointFactory


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
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._output_s3_uri == (
            f"s3://algorithm-endpoints-input//io/algorithms/endpoint/{endpoint.pk}/successes"
        )

    def test_failure_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME = (
            "algorithm-endpoints-input"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._failure_s3_uri == (
            f"s3://algorithm-endpoints-input//io/algorithms/endpoint/{endpoint.pk}/failures"
        )

    def test_endpoint_invocation_environment(self, settings):
        settings.COMPONENTS_INPUT_BUCKET_NAME = "test_components_input_bucket"
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator.invocation_environment == {
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "no_proxy": "amazonaws.com",
            "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": "7168",
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX": "",
            "GRAND_CHALLENGE_COMPONENT_API_METHOD": endpoint.algorithm_image.api_method,
            "GRAND_CHALLENGE_COMPONENT_MODEL": f"s3://test_components_input_bucket//auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz",
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
                    },
                },
                "ProductionVariants": [
                    {
                        "VariantName": endpoint.endpoint_name,
                        "ContainerStartupHealthCheckTimeoutInSeconds": 300,
                        "InitialInstanceCount": 1,
                        "InitialVariantWeight": 1,
                        "InstanceType": orchestrator._instance_type.name,
                        "ManagedInstanceScaling": {
                            "MaxInstanceCount": 1,
                            "MinInstanceCount": 1,
                            "Status": "ENABLED",
                        },
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
