import boto3
from django.conf import settings

from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)


class EndpointOrchestrator:
    def __init__(
        self,
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

        self.__sagemaker_runtime_client = None

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
