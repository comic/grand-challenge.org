import logging

from django.conf import settings

from grandchallenge.components.backends.amazon_sagemaker_base import (
    AmazonSageMakerBaseExecutor,
    LogStreamNotFound,
)
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    TaskCancelled,
)
from grandchallenge.components.backends.utils import (
    LOGLINES,
    get_sagemaker_model_name,
)

logger = logging.getLogger(__name__)


class AmazonSageMakerBatchExecutor(AmazonSageMakerBaseExecutor):
    @property
    def _log_group_name(self):
        # Hardcoded by AWS
        return "/aws/sagemaker/TransformJobs"

    @property
    def _metric_instance_prefix(self):
        return "i-"

    @staticmethod
    def get_job_name(*, event):
        return event["TransformJobName"]

    def _get_job_status(self, *, event):
        return event["TransformJobStatus"]

    def _get_start_time(self, *, event):
        return event.get("TransformStartTime")

    def _get_end_time(self, *, event):
        return event.get("TransformEndTime")

    def _get_instance_name(self, *, event):
        return event["TransformResources"]["InstanceType"]

    def _create_job_boto(self):
        self._sagemaker_client.create_transform_job(
            TransformJobName=self._sagemaker_job_name,
            ModelName=get_sagemaker_model_name(
                repo_tag=self._exec_image_repo_tag
            ),
            TransformInput={
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self._invocation_key}",
                    }
                }
            },
            TransformOutput={
                "S3OutputPath": f"s3://{settings.COMPONENTS_OUTPUT_BUCKET_NAME}/{self._invocation_prefix}"
            },
            TransformResources={
                "InstanceType": self._instance_type.name,
                "InstanceCount": 1,
            },
            Environment=self.invocation_environment,
            ModelClientConfig={
                "InvocationsTimeoutInSeconds": self._time_limit,
                "InvocationsMaxRetries": 0,
            },
        )

    def _stop_job_boto(self):
        self._sagemaker_client.stop_transform_job(
            TransformJobName=self._sagemaker_job_name
        )

    def deprovision(self):
        super().deprovision()

        self._delete_objects(
            bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            prefix=self._invocation_prefix,
        )

    def _handle_stopped_job(self, *, event):
        raise TaskCancelled

    def _handle_failed_job(self, *args, **kwargs):
        try:
            data_log = self._get_job_data_log()
        except LogStreamNotFound as error:
            logger.warning(str(error))
            data_log = []

        if any(
            "Model server did not respond to /invocations request within" in e
            for e in data_log
        ):
            raise ComponentException("Time limit exceeded")

        super()._handle_failed_job(*args, **kwargs)

    def _get_job_data_log(self):
        response = self._logs_client.get_log_events(
            logGroupName=self._log_group_name,
            logStreamName=self._get_log_stream_name(data_log=True),
            limit=LOGLINES,
            startFromHead=False,
        )
        return [event["message"] for event in response["events"]]
