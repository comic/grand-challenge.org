import botocore
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils._os import safe_join
from django.utils.html import format_html

from grandchallenge.components.backends.amazon_sagemaker_base import (
    AmazonSageMakerBaseExecutor,
)
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    TaskCancelled,
)


class AmazonSageMakerTrainingExecutor(AmazonSageMakerBaseExecutor):
    @property
    def _log_group_name(self):
        # Hardcoded by AWS
        return "/aws/sagemaker/TrainingJobs"

    @property
    def _metric_instance_prefix(self):
        return "algo-1"

    @property
    def _training_output_prefix(self):
        return safe_join("/training-outputs", *self.job_path_parts)

    @property
    def external_admin_url(self):
        return format_html(
            "https://{region}.console.aws.amazon.com/sagemaker/home#/jobs/{job_name}",
            job_name=self._sagemaker_job_name,
            region=settings.COMPONENTS_AMAZON_ECR_REGION
            or settings.AWS_DEFAULT_REGION,
        )

    @property
    def warm_pool_retained_billable_time_in_seconds(self):
        try:
            job_description = self._sagemaker_client.describe_training_job(
                TrainingJobName=self._sagemaker_job_name,
            )
        except botocore.exceptions.ClientError as error:
            if (
                error.response["Error"]["Code"] == "ValidationException"
                and "Requested resource not found"
                in error.response["Error"]["Message"]
            ):
                raise ObjectDoesNotExist from error
            else:
                raise

        if job_description.get("WarmPoolStatus", {}).get("Status") in {
            "Terminated",
            "Reused",
        }:
            return job_description["WarmPoolStatus"][
                "ResourceRetainedBillableTimeInSeconds"
            ]
        else:
            return None

    @staticmethod
    def get_job_name(*, event):
        return event["TrainingJobName"]

    def _get_job_status(self, *, event):
        return event["TrainingJobStatus"]

    def _get_start_time(self, *, event):
        return event.get("TrainingStartTime")

    def _get_end_time(self, *, event):
        return event.get("TrainingEndTime")

    def _get_instance_name(self, *, event):
        return event["ResourceConfig"]["InstanceType"]

    def _create_job_boto(self):
        self._sagemaker_client.create_training_job(
            TrainingJobName=self._sagemaker_job_name,
            AlgorithmSpecification={
                # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_AlgorithmSpecification.html
                "TrainingInputMode": "File",  # Pipe | File | FastFile
                "TrainingImage": self._exec_image_repo_tag,
                "ContainerArguments": [
                    "invoke",
                    "--file",
                    f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self._invocation_key}",
                ],
            },
            RoleArn=settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN,
            OutputDataConfig={
                # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_OutputDataConfig.html
                "S3OutputPath": f"s3://{settings.COMPONENTS_OUTPUT_BUCKET_NAME}/{self._training_output_prefix}",
            },
            ResourceConfig={
                # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ResourceConfig.html
                "VolumeSizeInGB": self._required_volume_size_gb,
                "InstanceType": self._instance_type.name,
                "InstanceCount": 1,
                "KeepAlivePeriodInSeconds": 300 if self._use_warm_pool else 0,
            },
            StoppingCondition={
                # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_StoppingCondition.html
                "MaxRuntimeInSeconds": int(self._time_limit.total_seconds()),
            },
            Environment={
                **self.invocation_environment,
            },
            VpcConfig={
                "SecurityGroupIds": [
                    settings.COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID
                ],
                "Subnets": settings.COMPONENTS_AMAZON_SAGEMAKER_SUBNETS,
            },
            RemoteDebugConfig={"EnableRemoteDebug": False},
        )

    def _stop_job_boto(self):
        self._sagemaker_client.stop_training_job(
            TrainingJobName=self._sagemaker_job_name
        )

    def deprovision(self):
        super().deprovision()

        self._delete_objects(
            bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            prefix=self._training_output_prefix,
        )

    def _handle_stopped_job(self, *, event):
        if event["TrainingJobStatus"] != "Stopped":
            raise RuntimeError("TrainingJobStatus should be 'Stopped'")

        secondary_status = event["SecondaryStatus"]

        # See https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeTrainingJob.html#sagemaker-DescribeTrainingJob-response-SecondaryStatus
        if secondary_status == "MaxRuntimeExceeded":
            raise ComponentException("Time limit exceeded")
        elif secondary_status == "Stopped":
            raise TaskCancelled
        else:
            raise RuntimeError(f"Unknown status {secondary_status!r}")
