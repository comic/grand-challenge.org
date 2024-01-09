from django.conf import settings
from django.utils._os import safe_join

from grandchallenge.components.backends.amazon_sagemaker_base import (
    AmazonSageMakerBaseExecutor,
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
                "VolumeSizeInGB": 30,  # Matches SageMaker Batch Inference
                "InstanceType": self._instance_type.name,
                "InstanceCount": 1,
            },
            StoppingCondition={
                # https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_StoppingCondition.html
                "MaxRuntimeInSeconds": self._time_limit,
            },
            Environment={
                **self.invocation_environment,
                # https://docs.aws.amazon.com/sagemaker/latest/dg/model-train-storage.html#model-train-storage-env-var-summary
                "GRAND_CHALLENGE_COMPONENT_WRITABLE_DIRECTORIES": "/opt/ml/output/data:/opt/ml/model:/opt/ml/checkpoints:/tmp",
            },
            VpcConfig={
                "SecurityGroupIds": [
                    settings.COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID
                ],
                "Subnets": settings.COMPONENTS_AMAZON_SAGEMAKER_SUBNETS,
            },
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

    def _get_invocation_json(self, *args, **kwargs):
        # SageMaker Training Jobs expect a list
        invocation_json = super()._get_invocation_json(*args, **kwargs)

        if not isinstance(invocation_json, dict):
            raise RuntimeError(
                "Expected to receive a single invocation JSON object"
            )

        return [invocation_json]
