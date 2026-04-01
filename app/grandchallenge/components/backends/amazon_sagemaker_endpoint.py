import boto3
from django.conf import settings

from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)


class EndpointOrchestrator:
    def __init__(
        self,
        endpoint_name,
        endpoint_id,
        exec_image_repo_tag,
        time_limit_seconds,
        requires_gpu_type,
        requires_memory_gb,
        api_method,
        algorithm_model,
    ):
        self._executor = AmazonSageMakerTrainingExecutor(
            job_id=endpoint_id,
            exec_image_repo_tag=exec_image_repo_tag,
            memory_limit=requires_memory_gb,
            time_limit=time_limit_seconds,
            requires_gpu_type=requires_gpu_type,
            use_warm_pool=False,
            signing_key=b"",  # TODO add signing key to endpoint model
            api_method=api_method,
            algorithm_model=algorithm_model,
        )
        self._endpoint_name = endpoint_name
        self._exec_image_repo_tag = exec_image_repo_tag

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
        return f"s3://{settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME}{self._algorithm_model_key}"

    @property
    def _output_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME}{self._io_prefix}/successes"

    @property
    def _failure_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_IO_BUCKET_NAME}{self._io_prefix}/failures"

    @property
    def _model_environment(self):
        return self._executor.invocation_environment

    @property
    def _instance_type(self):
        return self._executor._instance_type

    @property
    def _required_volume_size_gb(self):
        if self._instance_type.nvme_volume_size:
            # This setting has no practical effect as the instances
            # do not get an EBS volume
            return self._instance_type.nvme_volume_size
        else:
            return 30

    def create_sagemaker_model(self):
        self._sagemaker_client.create_model(
            ModelName=self._endpoint_name,
            ExecutionRoleArn=settings.ALGORITHM_ENDPOINTS_EXECUTION_ROLE_ARN,
            PrimaryContainer={
                "Image": self._exec_image_repo_tag,
                "Environment": self._model_environment,
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
                    "ManagedInstanceScaling": {
                        "MaxInstanceCount": 1,
                        "MinInstanceCount": 1,
                        "Status": "ENABLED",
                    },
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
