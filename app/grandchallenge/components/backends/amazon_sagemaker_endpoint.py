import logging
import re
from datetime import datetime, timedelta
from typing import NamedTuple
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from lambda_tasks.logging import task_logger

from grandchallenge.components.backends.amazon_sagemaker_training import (
    AmazonSageMakerTrainingExecutor,
)
from grandchallenge.components.backends.base import (
    list_and_delete_objects_from_prefix,
)
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import UUID4_REGEX
from grandchallenge.core.error_messages import SystemErrorMessages

logger = logging.getLogger(__name__)


class ObjectParams(NamedTuple):
    app_label: str
    model_name: str
    pk: UUID


class AmazonSageMakerEndpointOrchestrator(AmazonSageMakerTrainingExecutor):
    def __init__(
        self,
        endpoint_name,
        job_id,
        exec_image_repo_tag,
        requires_gpu_type,
        memory_limit,
        api_method,
        signing_key,
        time_limit=settings.ALGORITHM_ENDPOINTS_MAXIMUM_INVOCATION_DURATION,
        algorithm_model=None,
        runtime_setup_result_key=None,
    ):
        super().__init__(
            job_id=job_id,
            exec_image_repo_tag=exec_image_repo_tag,
            memory_limit=memory_limit,
            time_limit=time_limit,
            requires_gpu_type=requires_gpu_type,
            use_warm_pool=False,
            signing_key=signing_key,
            api_method=api_method,
            algorithm_model=None,
            input_bucket_name=settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME,
            output_bucket_name=settings.ALGORITHM_ENDPOINTS_OUTPUT_BUCKET_NAME,
            use_task_list=False,
        )
        self._endpoint_name = endpoint_name
        self._exec_image_repo_tag = exec_image_repo_tag
        self._algorithm_model = algorithm_model

        self.__sagemaker_runtime_client = None
        self.__runtime_setup_result_key = runtime_setup_result_key

    @property
    def _sagemaker_runtime_client(self):
        if self.__sagemaker_runtime_client is None:
            self.__sagemaker_runtime_client = boto3.client(
                "sagemaker-runtime",
                region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
            )
        return self.__sagemaker_runtime_client

    @property
    def _sagemaker_job_name(self):
        return self._endpoint_name

    def _get_start_time(self, *, event):
        return int(
            datetime.fromisoformat(event.get("receivedTime")).timestamp()
            * 1000
        )

    def _get_end_time(self, *, event):
        return int(
            datetime.fromisoformat(event.get("eventTime")).timestamp() * 1000
        )

    @property
    def runtime_setup_result_key(self):
        if self.__runtime_setup_result_key:
            return self.__runtime_setup_result_key
        else:
            return super().runtime_setup_result_key

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
    def _invocation_s3_uri(self):
        return f"s3://{settings.ALGORITHM_ENDPOINTS_INPUT_BUCKET_NAME}/{self._invocation_key}"

    @property
    def invocation_environment(self):
        env = super().invocation_environment

        if self._algorithm_model:
            env["GRAND_CHALLENGE_COMPONENT_MODEL"] = (
                self._algorithm_model_s3_uri
            )
        return env

    @property
    def _required_volume_size_gb(self):
        if self._instance_type.nvme_volume_size:
            # This setting has no practical effect as the instances
            # do not get an EBS volume
            return self._instance_type.nvme_volume_size
        else:
            return 30

    @property
    def time_limit(self):
        # Add buffer time to upload invocation result
        return self._time_limit + timedelta(seconds=10)

    @property
    def _auxiliary_data_provisioning_tasks(self):
        # Auxiliary data is handled separately. Return an empty list to remove
        # these from the list of provisioning tasks. That list is used during
        # provisioning for an invocation.
        return []

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
                    "NotificationConfig": {
                        "SuccessTopic": settings.ALGORITHM_ENDPOINTS_SNS_TOPIC_ARN,
                        "ErrorTopic": settings.ALGORITHM_ENDPOINTS_SNS_TOPIC_ARN,
                    },
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

    @staticmethod
    def get_endpoint_name(*, event):
        return event["EndpointName"]

    @staticmethod
    def _get_endpoint_status(*, event):
        return event["EndpointStatus"]

    @staticmethod
    def get_endpoint_params(*, endpoint_name):
        prefix_regex = re.escape(settings.COMPONENTS_REGISTRY_PREFIX)
        pattern = rf"^{prefix_regex}\-AE\-(?P<pk>{UUID4_REGEX})$"

        result = re.match(pattern, endpoint_name)

        if result is None:
            raise ValueError("Invalid endpoint name")
        else:
            pk = result.group("pk")
            return ObjectParams(
                app_label="algorithms",
                model_name="endpoint",
                pk=pk,
            )

    def handle_status_event(self, *, event):
        endpoint_status = self._get_endpoint_status(event=event)

        if endpoint_status == "IN_SERVICE":
            return
        elif endpoint_status == "FAILED":
            # Requires investigation
            task_logger.info(event)
            task_logger.error("Starting endpoint failed")
            raise ComponentException(SystemErrorMessages.UNEXPECTED_ERROR)
        else:
            raise ValueError("Invalid endpoint status")

    def provision_invocation_input_data(self, *, input_civs):
        super().provision(input_civs=input_civs, input_prefixes={})

    def invoke_endpoint(self, *, inference_id):
        self._sagemaker_runtime_client.invoke_endpoint_async(
            EndpointName=self._endpoint_name,
            ContentType="application/json",
            InputLocation=self._invocation_s3_uri,
            InferenceId=inference_id,
            InvocationTimeoutSeconds=int(self.time_limit.total_seconds()),
        )

    @staticmethod
    def get_inference_id(*, event):
        return event["inferenceId"]

    @staticmethod
    def _get_invocation_status(*, event):
        return event["invocationStatus"]

    @staticmethod
    def get_invocation_params(*, inference_id):
        prefix_regex = re.escape(settings.COMPONENTS_REGISTRY_PREFIX)
        pattern = rf"^{prefix_regex}\-AEI\-(?P<pk>{UUID4_REGEX})$"

        result = re.match(pattern, inference_id)

        if result is None:
            raise ValueError("Invalid inference id")
        else:
            pk = result.group("pk")
            return ObjectParams(
                app_label="algorithms",
                model_name="invocation",
                pk=pk,
            )

    def handle_event(self, *, event):
        invocation_status = self._get_invocation_status(event=event)

        if invocation_status == "Completed":
            self._handle_completed_invocation()
        elif invocation_status == "Expired":
            self._handle_expired_invocation(event=event)
        elif invocation_status == "Failed":
            self._handle_failed_invocation(event=event)
        else:
            raise ValueError("Invalid invocation status")

    def _handle_completed_invocation(self):
        super()._handle_completed_job()

    def _handle_expired_invocation(self, *, event):
        # Requires investigation
        task_logger.info(event)
        task_logger.error("Endpoint invocation expired")
        raise ComponentException(SystemErrorMessages.UNEXPECTED_ERROR)

    def _handle_failed_invocation(self, *, event):
        # Requires investigation
        task_logger.info(event)
        task_logger.error("Endpoint invocation failed")
        raise ComponentException(SystemErrorMessages.UNEXPECTED_ERROR)
