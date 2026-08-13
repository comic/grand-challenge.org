import json
import logging
import re
from datetime import timedelta
from functools import cached_property
from json import JSONDecodeError
from typing import NamedTuple

import boto3
import botocore
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import TextChoices
from django.utils._os import safe_join
from django.utils.html import format_html
from django.utils.timezone import now

from grandchallenge.charts.specs import components_line
from grandchallenge.components.backends.amazon_sagemaker_base import (
    INSTANCE_OPTIONS,
    AmazonSageMakerBaseExecutor,
)
from grandchallenge.components.backends.base import JobParams
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    RetryStep,
    RetryTask,
    TaskCancelled,
    UncleanExit,
)
from grandchallenge.components.backends.utils import (
    UUID4_REGEX,
    ms_timestamp_to_datetime,
)
from grandchallenge.core.error_messages import SystemErrorMessages
from grandchallenge.evaluation.utils import get

logger = logging.getLogger(__name__)


class LogStreamNotFound(Exception):
    """Raised when a log stream could not be found"""


class SourceChoices(TextChoices):
    STDOUT = "stdout"
    STDERR = "stderr"


class ParsedLog(NamedTuple):
    message: str
    source: SourceChoices


class ModelChoices(TextChoices):
    # The values must be short
    # The labels must be in the form "<app_label>-<model_name>"
    ALGORITHMS_JOB = "A", "algorithms-job"
    EVALUATION_EVALUATION = "E", "evaluation-evaluation"


class AmazonSageMakerTrainingLogsService:
    def __init__(self, *args, job_id, **kwargs):
        super().__init__(*args, **kwargs)

        self._job_id = job_id

        self.__sagemaker_client = None
        self.__logs_client = None
        self.__cloudwatch_client = None

    @property
    def _log_group_name(self):
        # Hardcoded by AWS
        return "/aws/sagemaker/TrainingJobs"

    @property
    def _metric_instance_prefix(self):
        # Hardcoded by AWS
        return "algo-1"

    @cached_property
    def _describe_job(self):
        try:
            return self._sagemaker_client.describe_training_job(
                TrainingJobName=self._sagemaker_job_name
            )
        except ClientError as error:
            if error.response["Error"]["Code"] == "ValidationException":
                raise LogStreamNotFound("Job does not exist") from error
            else:
                raise

    @property
    def _logging_start_time(self):
        # If a job has not been started then neither the start time
        # nor stop time will exist.
        start_time = self._describe_job.get("TrainingStartTime") or now()
        return start_time - timedelta(minutes=1)

    @property
    def _logging_end_time(self):
        # If the job has not started or has not stopped then look
        # at the logs until now.
        end_time = self._describe_job.get("TrainingEndTime") or now()
        return end_time + timedelta(minutes=1)

    @property
    def _instance_name(self):
        return self._describe_job["ResourceConfig"]["InstanceType"]

    @property
    def _sagemaker_job_name(self):
        # SageMaker requires job names to be less than 63 chars
        job_name = f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self._job_id}"

        for value, label in ModelChoices.choices:
            job_name = job_name.replace(label, value)

        return job_name

    @property
    def _sagemaker_client(self):
        if self.__sagemaker_client is None:
            self.__sagemaker_client = boto3.client(
                "sagemaker",
                region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
            )
        return self.__sagemaker_client

    @property
    def _logs_client(self):
        if self.__logs_client is None:
            self.__logs_client = boto3.client(
                "logs", region_name=settings.COMPONENTS_AMAZON_ECR_REGION
            )
        return self.__logs_client

    @property
    def _cloudwatch_client(self):
        if self.__cloudwatch_client is None:
            self.__cloudwatch_client = boto3.client(
                "cloudwatch",
                region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
            )
        return self.__cloudwatch_client

    @property
    def execution_history(self):
        transistions = self._describe_job["SecondaryStatusTransitions"]

        for transition in transistions:
            if (
                settings.COMPONENTS_REGISTRY_PREFIX
                in transition["StatusMessage"]
            ):
                # Strip out "Resource reused by training job: " messages
                # and anything else that may contain an arn
                transition["StatusMessage"] = ""
            else:
                # Avoid confusion around training vs inference
                transition["StatusMessage"] = (
                    transition["StatusMessage"]
                    .replace("Training", "Execution")
                    .replace("training", "execution")
                )

            transition["Status"] = transition["Status"].replace(
                "Training", "Executing"
            )

        return transistions

    @cached_property
    def _log_stream_name(self):
        response = self._logs_client.describe_log_streams(
            logGroupName=self._log_group_name,
            logStreamNamePrefix=self._sagemaker_job_name,
        )

        if "nextToken" in response:
            raise LogStreamNotFound("Too many log streams found")

        log_streams = {s["logStreamName"] for s in response["logStreams"]}

        if len(log_streams) == 1:
            return log_streams.pop()
        else:
            raise LogStreamNotFound("Log stream not found")

    @property
    def task_logs(self):
        output = []

        for log_event in self._log_events:
            try:
                parsed_log = self._parse_structured_log(
                    log=log_event["message"].replace("\x00", "")
                )
                timestamp = ms_timestamp_to_datetime(log_event["timestamp"])
            except (JSONDecodeError, KeyError, ValueError):
                logger.warning("Could not parse log")
                continue

            if parsed_log is not None:
                output.append(
                    (
                        timestamp,
                        parsed_log,
                    )
                )

        return output

    @cached_property
    def _log_events(self):
        log_events = []

        try:
            log_stream_name = self._log_stream_name
        except LogStreamNotFound as error:
            logger.warning(str(error))
            return log_events

        n_calls = 0
        next_token = None

        call_args = {
            "logGroupName": self._log_group_name,
            "logStreamName": log_stream_name,
            "startFromHead": False,
            "startTime": int(self._logging_start_time.timestamp() * 1000),
            "endTime": int(self._logging_end_time.timestamp() * 1000),
        }

        while n_calls < 2:
            if next_token:
                call_args["nextToken"] = next_token

            response = self._logs_client.get_log_events(**call_args)
            n_calls += 1

            # Prepend the new events as we are working backwards with
            # nextBackwardToken and startFromHead = False
            log_events = response["events"] + log_events
            new_token = response["nextBackwardToken"]

            if new_token == next_token:
                break
            else:
                next_token = new_token

        return log_events

    @staticmethod
    def _parse_structured_log(*, log: str) -> ParsedLog | None:
        """Parse the structured logs from SageMaker Shim"""
        structured_log = json.loads(log.strip())

        message = structured_log["log"]
        source = SourceChoices(structured_log["source"])

        # Defensive, in case the type of structured_log["internal"] is str
        if structured_log["internal"] is False:
            return ParsedLog(
                message=message,
                source=source,
            )
        else:
            return None

    @cached_property
    def _runtime_metrics(self):
        started = self._logging_start_time
        stopped = self._logging_end_time

        query_id = "q"
        query = f"SEARCH('{{{self._log_group_name},Host}} Host={self._sagemaker_job_name}/{self._metric_instance_prefix}', 'Average', 60)"

        instance_type = get(
            [
                instance
                for instance in INSTANCE_OPTIONS
                if instance.name == self._instance_name
            ]
        )

        response = self._cloudwatch_client.get_metric_data(
            MetricDataQueries=[{"Id": query_id, "Expression": query}],
            StartTime=started,
            EndTime=stopped,
        )

        if "NextToken" in response:
            logger.error("Too many metrics found")

        runtime_metrics = [
            {
                "label": metric["Label"],
                "status": metric["StatusCode"],
                "timestamps": [t.isoformat() for t in metric["Timestamps"]],
                "values": metric["Values"],
            }
            for metric in response["MetricDataResults"]
            if metric["Id"] == query_id
        ]

        return {
            "instance": {
                "name": instance_type.name,
                "cpu": instance_type.cpu,
                "memory": instance_type.memory,
                "gpus": instance_type.gpus,
                "gpu_type": (
                    None
                    if instance_type.gpu_type is None
                    else instance_type.gpu_type.value
                ),
            },
            "metrics": runtime_metrics,
        }

    @property
    def runtime_metrics_chart(self):
        instance_metrics = self._runtime_metrics["instance"]
        n_cpu = instance_metrics["cpu"]

        if instance_metrics["gpus"]:
            gpu_str = (
                f"{instance_metrics['gpus']}x {instance_metrics['gpu_type']}"
            )
        else:
            gpu_str = "No"

        title = f"{instance_metrics['name']} / {instance_metrics['cpu']} CPU / {instance_metrics['memory']} GB Memory / {gpu_str} GPU"

        return components_line(
            values=[
                {
                    "Metric": metric["label"],
                    "Timestamp": timestamp,
                    "Percent": (
                        value / (n_cpu * 100.0)
                        if metric["label"] == "CPUUtilization"
                        else value / 100.0
                    ),
                }
                for metric in self._runtime_metrics["metrics"]
                for timestamp, value in zip(
                    metric["timestamps"], metric["values"], strict=True
                )
            ],
            title=title,
            single_thread_limit=100.0 / n_cpu,
            tooltip=[
                {
                    "field": metric["label"],
                    "type": "quantitative",
                    "format": ".2%",
                }
                for metric in self._runtime_metrics["metrics"]
            ],
        )


class AmazonSageMakerTrainingExecutor(AmazonSageMakerBaseExecutor):
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

    @property
    def _required_volume_size_gb(self):
        required_gb = super()._required_volume_size_gb

        if self._instance_type.nvme_volume_size:
            if required_gb > self._instance_type.nvme_volume_size:
                logger.error(
                    f"Job {self._job_id} likely needs {required_gb} GB but "
                    f"instance only has {self._instance_type.nvme_volume_size} GB. "
                    "Attempting to run the job anyway."
                )
            # Always request the nvme size for instances that offer it
            # This setting has no practical effect as the instances
            # do not get an EBS volume, but allows the instance
            # to be reused in a warm pool as it is included in
            # SageMakers warm pool reuse logic
            return self._instance_type.nvme_volume_size
        else:
            if required_gb > settings.COMPONENTS_EBS_VOLUME_SIZE_LIMIT_GB:
                logger.error(
                    f"Job {self._job_id} likely needs {required_gb} GB but "
                    f"instance is limited to {settings.COMPONENTS_EBS_VOLUME_SIZE_LIMIT_GB} GB due to EBS limits. "
                    "Attempting to run the job anyway."
                )
                return settings.COMPONENTS_EBS_VOLUME_SIZE_LIMIT_GB
            else:
                return required_gb

    @property
    def _sagemaker_job_name(self):
        # SageMaker requires job names to be less than 63 chars
        job_name = f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self._job_id}"

        for value, label in ModelChoices.choices:
            job_name = job_name.replace(label, value)

        return job_name

    @staticmethod
    def get_job_params(*, job_name):
        prefix_regex = re.escape(settings.COMPONENTS_REGISTRY_PREFIX)
        model_regex = r"|".join(ModelChoices.values)
        pattern = rf"^{prefix_regex}\-(?P<job_model>{model_regex})\-(?P<job_pk>{UUID4_REGEX})\-(?P<attempt>\d{{2}})$"

        result = re.match(pattern, job_name)

        if result is None:
            raise ValueError("Invalid job name")
        else:
            job_model = ModelChoices(result.group("job_model")).label
            job_app_label, job_model_name = job_model.split("-")
            job_pk = result.group("job_pk")
            attempt = int(result.group("attempt"))
            return JobParams(
                app_label=job_app_label,
                model_name=job_model_name,
                pk=job_pk,
                attempt=attempt,
            )

    @staticmethod
    def get_job_name(*, event):
        return event["TrainingJobName"]

    def _get_job_status(self, *, event):
        return event["TrainingJobStatus"]

    def _get_start_time(self, *, event):
        return event.get("TrainingStartTime")

    def _get_end_time(self, *, event):
        return event.get("TrainingEndTime")

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

    def execute(self):
        self._create_sagemaker_job()

    def handle_event(self, *, event):
        job_status = self._get_job_status(event=event)

        self._set_duration(event=event)

        if job_status == "Completed":
            self._handle_completed_job()
        elif job_status == "Stopped":
            self._handle_stopped_job(event=event)
        elif job_status == "Failed":
            self._handle_failed_job(event=event)
        else:
            raise ValueError("Invalid job status")

    def deprovision(self):
        self._stop_running_jobs()

        super().deprovision()

        self._delete_objects(
            bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            prefix=self._invocation_prefix,
        )

        self._delete_objects(
            bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            prefix=self._training_output_prefix,
        )

    def _create_sagemaker_job(self):
        try:
            self._create_job_boto()
        except (
            self._sagemaker_client.exceptions.ResourceLimitExceeded
        ) as error:
            raise RetryStep("Capacity Limit Exceeded") from error
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "ThrottlingException":
                raise RetryStep("Request throttled") from error
            else:
                raise error

    def _handle_stopped_job(self, *, event):
        if event["TrainingJobStatus"] != "Stopped":
            raise RuntimeError("TrainingJobStatus should be 'Stopped'")

        secondary_status = event["SecondaryStatus"]

        # See https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_DescribeTrainingJob.html#sagemaker-DescribeTrainingJob-response-SecondaryStatus
        if secondary_status == "MaxRuntimeExceeded":
            raise ComponentException(SystemErrorMessages.TIME_LIMIT_EXCEEDED)
        elif secondary_status == "Stopped":
            raise TaskCancelled
        else:
            raise RuntimeError(f"Unknown status {secondary_status!r}")

    def _handle_failed_job(self, *, event):
        failure_reason = event.get("FailureReason")

        if failure_reason == (
            "CapacityError: Unable to provision requested ML compute capacity. "
            "Please retry using a different ML instance type."
        ):
            raise RetryTask("No current capacity for the chosen instance type")

        if failure_reason == (
            "InternalServerError: We encountered an internal error. "
            "Please try again."
        ):
            if (
                self.get_job_params(
                    job_name=self.get_job_name(event=event)
                ).attempt
                < 1
            ):
                raise RetryTask("Retrying due to internal server error")
            else:
                raise ComponentException("Container image would not start")
        elif failure_reason in (
            "ClientError: Please use an instance type with more memory, "
            "or reduce the size of job data processed on an instance.",
            "ClientError: Artifact upload failed:ClientError: "
            "Out of Memory. Please use a larger instance",
        ):
            try:
                users_process_exit_code = (
                    self._get_inference_result().return_code
                )
            except UncleanExit:
                users_process_exit_code = None

            if users_process_exit_code not in (-9, 1, 137):
                # Requires investigation
                logger.error(f"SageMaker OOM {users_process_exit_code=}")

            raise ComponentException(SystemErrorMessages.MEMORY_LIMIT_EXCEEDED)
        else:
            # Requires investigation
            logger.error(f"SageMaker Job failed: {failure_reason}")

            raise ComponentException(SystemErrorMessages.UNEXPECTED_ERROR)

    def _stop_running_jobs(self):
        try:
            self._stop_job_boto()
        except botocore.exceptions.ClientError as error:
            okay_error_messages = {
                # Unstoppable job:
                "The request was rejected because the transform job is in status",
                "The request was rejected because the training job is in status",
                # Job was never created:
                "Could not find job to update with name",
                "Requested resource not found",
            }

            if error.response["Error"]["Code"] == "ThrottlingException":
                raise RetryStep("Request throttled") from error
            elif error.response["Error"][
                "Code"
            ] == "ValidationException" and any(
                okay_message in error.response["Error"]["Message"]
                for okay_message in okay_error_messages
            ):
                logger.info(f"The job could not be stopped: {error}")
            else:
                raise error
