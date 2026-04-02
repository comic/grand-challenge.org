from botocore.stub import Stubber

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
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._algorithm_model_s3_uri == (
            f"s3://interactive-algorithms-io/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz"
        )

    def test_output_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._output_s3_uri == (
            f"s3://interactive-algorithms-io/io/algorithms/endpoint/{endpoint.pk}/successes"
        )

    def test_failure_s3_uri(self, settings):
        settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME = (
            "interactive-algorithms-io"
        )
        endpoint = EndpointFactory.build()
        orchestrator = endpoint.orchestrator

        assert orchestrator._failure_s3_uri == (
            f"s3://interactive-algorithms-io/io/algorithms/endpoint/{endpoint.pk}/failures"
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
            "GRAND_CHALLENGE_COMPONENT_MODEL": f"s3://test_components_input_bucket/auxiliary-data/algorithms/endpoint/{endpoint.pk}/algorithm-model.tar.gz",
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
