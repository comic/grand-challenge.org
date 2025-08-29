import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from json import JSONDecodeError
from typing import NamedTuple

import boto3
import botocore
from django.conf import settings
from django.db.models import TextChoices
from django.utils.functional import cached_property

from grandchallenge.components.backends.base import Executor, JobParams
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    RetryStep,
    RetryTask,
    UncleanExit,
)
from grandchallenge.components.backends.utils import (
    LOGLINES,
    UUID4_REGEX,
    SourceChoices,
    ms_timestamp_to_datetime,
    parse_structured_log,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.evaluation.utils import get

logger = logging.getLogger(__name__)


class LogStreamNotFound(Exception):
    """Raised when a log stream could not be found"""


class InstanceType(NamedTuple):
    name: str
    cpu: int
    memory: float
    usd_cents_per_hour: int
    gpu_type: GPUTypeChoices
    gpus: int = 0
    nvme_volume_size: int | None = None


INSTANCE_OPTIONS = [
    # Instance types and pricing from eu-west-1, retrieved 17-JAN-2024
    # https://aws.amazon.com/sagemaker/pricing/
    InstanceType(
        name="ml.m7i.large",
        cpu=2,
        memory=8,
        usd_cents_per_hour=14,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.large",
        cpu=2,
        memory=16,
        usd_cents_per_hour=18,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.xlarge",
        cpu=4,
        memory=32,
        usd_cents_per_hour=36,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.2xlarge",
        cpu=8,
        memory=64,
        usd_cents_per_hour=72,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.4xlarge",
        cpu=16,
        memory=128,
        usd_cents_per_hour=143,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.8xlarge",
        cpu=32,
        memory=256,
        usd_cents_per_hour=285,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.12xlarge",
        cpu=48,
        memory=384,
        usd_cents_per_hour=426,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.16xlarge",
        cpu=64,
        memory=512,
        usd_cents_per_hour=569,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.24xlarge",
        cpu=96,
        memory=768,
        usd_cents_per_hour=853,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.48xlarge",
        cpu=192,
        memory=1536,
        usd_cents_per_hour=1706,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.p4d.24xlarge",
        cpu=96,
        memory=1152,
        usd_cents_per_hour=2728,
        gpus=8,
        gpu_type=GPUTypeChoices.A100,
        nvme_volume_size=8 * 1000,
    ),
    InstanceType(
        name="ml.p3.2xlarge",
        cpu=8,
        memory=61,
        usd_cents_per_hour=414,
        gpus=1,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3.8xlarge",
        cpu=32,
        memory=244,
        usd_cents_per_hour=1587,
        gpus=4,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3.16xlarge",
        cpu=64,
        memory=488,
        usd_cents_per_hour=3041,
        gpus=8,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3dn.24xlarge",
        cpu=96,
        memory=768,
        usd_cents_per_hour=3877,
        gpus=8,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p2.xlarge",
        cpu=4,
        memory=61,
        usd_cents_per_hour=122,
        gpus=1,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.p2.8xlarge",
        cpu=32,
        memory=488,
        usd_cents_per_hour=934,
        gpus=8,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.p2.16xlarge",
        cpu=64,
        memory=732,
        usd_cents_per_hour=1789,
        gpus=16,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.g5.xlarge",
        cpu=4,
        memory=16,
        usd_cents_per_hour=157,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=250,
    ),
    InstanceType(
        name="ml.g5.2xlarge",
        cpu=8,
        memory=32,
        usd_cents_per_hour=169,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=450,
    ),
    InstanceType(
        name="ml.g5.4xlarge",
        cpu=16,
        memory=64,
        usd_cents_per_hour=227,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=600,
    ),
    InstanceType(
        name="ml.g5.8xlarge",
        cpu=32,
        memory=128,
        usd_cents_per_hour=342,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g5.12xlarge",
        cpu=48,
        memory=192,
        usd_cents_per_hour=791,
        gpus=4,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=3800,
    ),
    InstanceType(
        name="ml.g5.16xlarge",
        cpu=64,
        memory=256,
        usd_cents_per_hour=572,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=1900,
    ),
    InstanceType(
        name="ml.g5.24xlarge",
        cpu=96,
        memory=384,
        usd_cents_per_hour=1136,
        gpus=4,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=3800,
    ),
    InstanceType(
        name="ml.g5.48xlarge",
        cpu=192,
        memory=768,
        usd_cents_per_hour=2273,
        gpus=8,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=2 * 3800,
    ),
    InstanceType(
        name="ml.g4dn.xlarge",
        cpu=4,
        memory=16,
        usd_cents_per_hour=83,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=125,
    ),
    InstanceType(
        name="ml.g4dn.2xlarge",
        cpu=8,
        memory=32,
        usd_cents_per_hour=105,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=225,
    ),
    InstanceType(
        name="ml.g4dn.4xlarge",
        cpu=16,
        memory=64,
        usd_cents_per_hour=168,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=225,
    ),
    InstanceType(
        name="ml.g4dn.8xlarge",
        cpu=32,
        memory=128,
        usd_cents_per_hour=304,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g4dn.12xlarge",
        cpu=48,
        memory=192,
        usd_cents_per_hour=546,
        gpus=4,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g4dn.16xlarge",
        cpu=64,
        memory=256,
        usd_cents_per_hour=607,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
]


class ModelChoices(TextChoices):
    # The values must be short
    # The labels must be in the form "<app_label>-<model_name>"
    ALGORITHMS_JOB = "A", "algorithms-job"
    EVALUATION_EVALUATION = "E", "evaluation-evaluation"


class AmazonSageMakerBaseExecutor(Executor, ABC):
    @property
    @abstractmethod
    def _log_group_name(self):
        pass

    @property
    @abstractmethod
    def _metric_instance_prefix(self):
        pass

    @abstractmethod
    def _get_job_status(self, *, event):
        pass

    @abstractmethod
    def _get_start_time(self, *, event):
        pass

    @abstractmethod
    def _get_end_time(self, *, event):
        pass

    @abstractmethod
    def _get_instance_name(self, *, event):
        pass

    @abstractmethod
    def _create_job_boto(self):
        pass

    @abstractmethod
    def _stop_job_boto(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__duration = None
        self.__runtime_metrics = {}

        self.__sagemaker_client = None
        self.__logs_client = None
        self.__cloudwatch_client = None

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
    def duration(self):
        return self.__duration

    @property
    def runtime_metrics(self):
        return self.__runtime_metrics

    @property
    def _sagemaker_job_name(self):
        # SageMaker requires job names to be less than 63 chars
        job_name = f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self._job_id}"

        for value, label in ModelChoices.choices:
            job_name = job_name.replace(label, value)

        return job_name

    @cached_property
    def _instance_type(self):
        """Find the cheapest instance that can run this job"""

        if self._requires_gpu_type == GPUTypeChoices.NO_GPU:
            n_gpu = 0
        else:
            # For now only use a single gpu
            n_gpu = 1

        compatible_instances = [
            instance
            for instance in INSTANCE_OPTIONS
            if instance.gpus == n_gpu
            and instance.gpu_type == self._requires_gpu_type
            and instance.memory >= self._memory_limit
        ]

        if not compatible_instances:
            raise ValueError("No suitable instance types for job")

        # Get the lowest priced instance
        compatible_instances.sort(key=lambda x: x.usd_cents_per_hour)
        return compatible_instances[0]

    @property
    def usd_cents_per_hour(self):
        return self._instance_type.usd_cents_per_hour

    @property
    def _max_memory_mb(self):
        # Reserve 1 GB for the system
        return (self._instance_type.memory - 1) * 1024

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
            return required_gb

    def execute(self):
        self._create_sagemaker_job()

    def handle_event(self, *, event):
        job_status = self._get_job_status(event=event)

        self._set_duration(event=event)
        self._set_task_logs(event=event)
        self._set_runtime_metrics(event=event)

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

    def _set_duration(self, *, event):
        try:
            started = ms_timestamp_to_datetime(
                self._get_start_time(event=event)
            )
            stopped = ms_timestamp_to_datetime(self._get_end_time(event=event))
            self.__duration = stopped - started
        except TypeError:
            logger.warning("Invalid start or end time, duration undetermined")
            self.__duration = None

    def _get_log_stream_name(self, *, data_log=False):
        response = self._logs_client.describe_log_streams(
            logGroupName=self._log_group_name,
            logStreamNamePrefix=f"{self._sagemaker_job_name}",
        )

        if "nextToken" in response:
            raise LogStreamNotFound("Too many log streams found")

        log_streams = {
            s["logStreamName"]
            for s in response["logStreams"]
            if s["logStreamName"].endswith("/data-log") is data_log
        }

        if len(log_streams) == 1:
            return log_streams.pop()
        else:
            raise LogStreamNotFound("Log stream not found")

    def _set_task_logs(self, *, event):
        stdout = []
        stderr = []

        for log_event in self._get_log_events(event=event):
            try:
                parsed_log = parse_structured_log(
                    log=log_event["message"].replace("\x00", "")
                )
                timestamp = ms_timestamp_to_datetime(log_event["timestamp"])
            except (JSONDecodeError, KeyError, ValueError):
                logger.warning("Could not parse log")
                continue

            if parsed_log is not None:
                output = f"{timestamp.isoformat()} {parsed_log.message}"
                if parsed_log.source == SourceChoices.STDOUT:
                    stdout.append(output)
                elif parsed_log.source == SourceChoices.STDERR:
                    stderr.append(output)
                else:
                    logger.error("Invalid source")

        self._stdout = stdout[-LOGLINES:] if len(stdout) > LOGLINES else stdout
        self._stderr = stderr[-LOGLINES:] if len(stderr) > LOGLINES else stderr

    def _get_log_events(self, *, event):
        log_events = []

        try:
            log_stream_name = self._get_log_stream_name(data_log=False)
        except LogStreamNotFound as error:
            logger.warning(str(error))
            return log_events

        n_calls = 0
        next_token = None

        call_args = {
            "logGroupName": self._log_group_name,
            "logStreamName": log_stream_name,
            "startFromHead": False,
            "startTime": self._get_start_time(event=event),
            "endTime": self._get_end_time(event=event),
        }

        while n_calls < 10:
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

    def _set_runtime_metrics(self, *, event):
        try:
            started = ms_timestamp_to_datetime(
                self._get_start_time(event=event)
            )
            stopped = ms_timestamp_to_datetime(self._get_end_time(event=event))
        except TypeError:
            logger.warning("Invalid start or end time, metrics undetermined")
            return

        query_id = "q"
        query = f"SEARCH('{{{self._log_group_name},Host}} Host={self._sagemaker_job_name}/{self._metric_instance_prefix}', 'Average', 60)"

        instance_type = get(
            [
                instance
                for instance in INSTANCE_OPTIONS
                if instance.name == self._get_instance_name(event=event)
            ]
        )

        response = self._cloudwatch_client.get_metric_data(
            MetricDataQueries=[{"Id": query_id, "Expression": query}],
            # Add buffer time to allow metrics to be delivered
            StartTime=started - timedelta(minutes=1),
            EndTime=stopped + timedelta(minutes=5),
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

        self.__runtime_metrics = {
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

    @abstractmethod
    def _handle_stopped_job(self, *, event):
        pass

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
                < 3
            ):
                raise RetryTask("Retrying due to internal server error")
            else:
                raise ComponentException(
                    "Algorithm container image would not start"
                )
        elif failure_reason in (
            "ClientError: Please use an instance type with more memory, "
            "or reduce the size of job data processed on an instance.",
            "ClientError: Artifact upload failed:ClientError: "
            "Out of Memory. Please use a larger instance",
        ):
            try:
                # Allow time for the log file to be written
                time.sleep(10)
                users_process_exit_code = self._get_task_return_code()
            except UncleanExit:
                users_process_exit_code = None

            if users_process_exit_code not in (-9, 1, 137):
                # Requires investigation
                logger.error(f"SageMaker OOM {users_process_exit_code=}")

            raise ComponentException(
                "The container was killed as it exceeded its memory limit"
            )
        else:
            # Requires investigation
            logger.error(f"SageMaker Job failed: {failure_reason}")

            raise ComponentException("An unexpected error occurred")

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
