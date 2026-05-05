import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)
from grandchallenge.components.backends.base import (
    list_and_delete_objects_from_prefix,
)


class EndpointOrchestrator:
    def __init__(
        self,
        endpoint_name,
        endpoint_id,
        exec_image_repo_tag,
        requires_gpu_type,
        memory_limit,
        api_method,
        signing_key,
        invocation_id=None,
        time_limit=settings.ALGORITHM_ENDPOINTS_MAXIMUM_INVOCATION_DURATION,
        algorithm_model=None,
    ):
        if invocation_id:
            job_id = invocation_id
        else:
            job_id = endpoint_id
        self._executor = AmazonSageMakerTrainingExecutor(
            job_id=job_id,
            exec_image_repo_tag=exec_image_repo_tag,
            memory_limit=memory_limit,
            time_limit=time_limit,
            requires_gpu_type=requires_gpu_type,
            use_warm_pool=False,
            signing_key=signing_key,
            api_method=api_method,
            algorithm_model=algorithm_model,
            input_bucket_name=settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME,
            output_bucket_name=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
        )
        self._endpoint_name = endpoint_name
        self._exec_image_repo_tag = exec_image_repo_tag
        self._algorithm_model = algorithm_model

        self.__sagemaker_runtime_client = None

    @property
    def _s3_client(self):
        return self._executor._s3_client

    @property
    def _sagemaker_client(self):
        return self._executor._sagemaker_client

    @property
    def _sagemaker_runtime_client(self):
        if self.__sagemaker_runtime_client is None:
            self.__sagemaker_runtime_client = boto3.client(
                "sagemaker-runtime",
                region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
            )
        return self.__sagemaker_runtime_client

    @property
    def _auxiliary_data_prefix(self):
        return self._executor._auxiliary_data_prefix

    @property
    def _io_prefix(self):
        return self._executor._io_prefix

    @property
    def _algorithm_model_key(self):
        return self._executor._algorithm_model_key

    @property
    def _algorithm_model_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME}/{self._algorithm_model_key}"

    @property
    def _output_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME}/{self._io_prefix}/successes"

    @property
    def _failure_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME}/{self._io_prefix}/failures"

    @property
    def invocation_environment(self):
        env = self._executor.invocation_environment

        if self._algorithm_model:
            env["GRAND_CHALLENGE_COMPONENT_MODEL"] = (
                self._algorithm_model_s3_uri
            )
        return env

    @property
    def _instance_type(self):
        return self._executor._instance_type

    @property
    def usd_cents_per_hour(self):
        return self._executor.usd_cents_per_hour

    @property
    def _required_volume_size_gb(self):
        if self._instance_type.nvme_volume_size:
            # This setting has no practical effect as the instances
            # do not get an EBS volume
            return self._instance_type.nvme_volume_size
        else:
            return 30

    def provision_auxiliary_data(self):
        if self._algorithm_model:
            self._s3_client.copy(
                CopySource={
                    "Bucket": settings.PROTECTED_S3_STORAGE_KWARGS[
                        "bucket_name"
                    ],
                    "Key": str(self._algorithm_model),
                },
                Bucket=settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME,
                Key=self._algorithm_model_key,
            )

    def deprovision_auxiliary_data(self):
        list_and_delete_objects_from_prefix(
            s3_client=self._s3_client,
            bucket=settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME,
            prefix=self._auxiliary_data_prefix,
        )

    def create_sagemaker_model(self):
        self._sagemaker_client.create_model(
            ModelName=self._endpoint_name,
            ExecutionRoleArn=settings.ALGORITHM_ENDPOINTS_EXECUTION_ROLE_ARN,
            PrimaryContainer={
                "Image": self._exec_image_repo_tag,
                "Environment": self.invocation_environment,
                "Mode": "SingleModel",
            },
            VpcConfig={
                "SecurityGroupIds": [
                    settings.ALGORITHM_ENDPOINTS_SECURITY_GROUP_ID
                ],
                "Subnets": settings.ALGORITHM_ENDPOINTS_SUBNETS,
            },
        )

    def delete_sagemaker_model(self):
        self._sagemaker_client.delete_model(ModelName=self._endpoint_name)

    def create_endpoint_config(self):
        self._sagemaker_client.create_endpoint_config(
            EndpointConfigName=self._endpoint_name,
            AsyncInferenceConfig={
                "ClientConfig": {
                    "MaxConcurrentInvocationsPerInstance": 1,
                },
                "OutputConfig": {
                    "S3FailurePath": self._failure_s3_uri,
                    "S3OutputPath": self._output_s3_uri,
                },
            },
            ProductionVariants=[
                {
                    "VariantName": self._endpoint_name,
                    "ContainerStartupHealthCheckTimeoutInSeconds": 300,
                    "InitialInstanceCount": 1,
                    "InitialVariantWeight": 1,
                    "InstanceType": self._instance_type.name,
                    "ModelName": self._endpoint_name,
                    "VolumeSizeInGB": self._required_volume_size_gb,
                }
            ],
        )

    def delete_endpoint_config(self):
        self._sagemaker_client.delete_endpoint_config(
            EndpointConfigName=self._endpoint_name
        )

    def create_endpoint(self):
        self._sagemaker_client.create_endpoint(
            EndpointName=self._endpoint_name,
            EndpointConfigName=self._endpoint_name,
        )

    def delete_endpoint(self):
        self._sagemaker_client.delete_endpoint(
            EndpointName=self._endpoint_name
        )

    def deprovision(self):
        def attempt(method):
            try:
                method()
            except ClientError as error:
                if (
                    error.response["Error"]["Code"] == "ValidationException"
                    and "Could not find" in error.response["Error"]["Message"]
                ):
                    pass  # Nothing to clean up
                else:
                    raise

        attempt(self.delete_endpoint)
        attempt(self.delete_endpoint_config)
        attempt(self.delete_sagemaker_model)

        self.deprovision_auxiliary_data()
