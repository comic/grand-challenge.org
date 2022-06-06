import io
import json
import logging
import re
from datetime import timedelta
from json import JSONDecodeError
from typing import NamedTuple, Optional

import boto3
from django.conf import settings
from django.db.models import TextChoices
from django.utils._os import safe_join

from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.exceptions import TaskCancelled
from grandchallenge.components.backends.utils import (
    LOGLINES,
    SourceChoices,
    get_sagemaker_model_name,
    ms_timestamp_to_datetime,
    parse_structured_log,
)

logger = logging.getLogger(__name__)

UUID4_REGEX = (
    r"[0-9a-f]{8}\-[0-9a-f]{4}\-4[0-9a-f]{3}\-[89ab][0-9a-f]{3}\-[0-9a-f]{12}"
)


class GPUChoices(TextChoices):
    V100 = "V100"
    K80 = "K80"
    T4 = "T4"


class InstanceType(NamedTuple):
    name: str
    cpu: int
    memory: float
    price_per_hour: float
    gpus: int = 0
    gpu_type: Optional[GPUChoices] = None


INSTANCE_OPTIONS = [
    # Instance types and pricing from eu-west-1, retrieved 06-JUN-2022
    # https://aws.amazon.com/sagemaker/pricing/
    InstanceType(
        name="ml.m5.large",
        cpu=2,
        memory=8,
        price_per_hour=0.128,
    ),
    InstanceType(
        name="ml.m5.xlarge",
        cpu=4,
        memory=16,
        price_per_hour=0.257,
    ),
    InstanceType(
        name="ml.m5.2xlarge",
        cpu=8,
        memory=32,
        price_per_hour=0.514,
    ),
    InstanceType(
        name="ml.m5.4xlarge",
        cpu=16,
        memory=64,
        price_per_hour=1.027,
    ),
    InstanceType(
        name="ml.m5.12xlarge",
        cpu=48,
        memory=192,
        price_per_hour=3.082,
    ),
    InstanceType(
        name="ml.m5.24xlarge",
        cpu=96,
        memory=384,
        price_per_hour=6.163,
    ),
    InstanceType(
        name="ml.m4.xlarge",
        cpu=4,
        memory=16,
        price_per_hour=0.266,
    ),
    InstanceType(
        name="ml.m4.2xlarge",
        cpu=8,
        memory=32,
        price_per_hour=0.533,
    ),
    InstanceType(
        name="ml.m4.4xlarge",
        cpu=16,
        memory=64,
        price_per_hour=1.066,
    ),
    InstanceType(
        name="ml.m4.10xlarge",
        cpu=40,
        memory=160,
        price_per_hour=2.664,
    ),
    InstanceType(
        name="ml.m4.16xlarge",
        cpu=64,
        memory=256,
        price_per_hour=4.262,
    ),
    InstanceType(
        name="ml.c5.xlarge",
        cpu=4,
        memory=8,
        price_per_hour=0.23,
    ),
    InstanceType(
        name="ml.c5.2xlarge",
        cpu=8,
        memory=16,
        price_per_hour=0.461,
    ),
    InstanceType(
        name="ml.c5.4xlarge",
        cpu=16,
        memory=32,
        price_per_hour=0.922,
    ),
    InstanceType(
        name="ml.c5.9xlarge",
        cpu=36,
        memory=72,
        price_per_hour=2.074,
    ),
    InstanceType(
        name="ml.c5.18xlarge",
        cpu=72,
        memory=144,
        price_per_hour=4.147,
    ),
    InstanceType(
        name="ml.c4.xlarge",
        cpu=4,
        memory=7.5,
        price_per_hour=0.271,
    ),
    InstanceType(
        name="ml.c4.2xlarge",
        cpu=8,
        memory=15,
        price_per_hour=0.544,
    ),
    InstanceType(
        name="ml.c4.4xlarge",
        cpu=16,
        memory=30,
        price_per_hour=1.086,
    ),
    InstanceType(
        name="ml.c4.8xlarge",
        cpu=36,
        memory=60,
        price_per_hour=2.173,
    ),
    InstanceType(
        name="ml.p3.2xlarge",
        cpu=8,
        memory=61,
        price_per_hour=4.131,
        gpus=1,
        gpu_type=GPUChoices.V100,
    ),
    InstanceType(
        name="ml.p3.8xlarge",
        cpu=32,
        memory=244,
        price_per_hour=15.864,
        gpus=4,
        gpu_type=GPUChoices.V100,
    ),
    InstanceType(
        name="ml.p3.16xlarge",
        cpu=64,
        memory=488,
        price_per_hour=30.406,
        gpus=8,
        gpu_type=GPUChoices.V100,
    ),
    InstanceType(
        name="ml.p2.xlarge",
        cpu=4,
        memory=61,
        price_per_hour=1.215,
        gpus=1,
        gpu_type=GPUChoices.K80,
    ),
    InstanceType(
        name="ml.p2.8xlarge",
        cpu=32,
        memory=488,
        price_per_hour=9.331,
        gpus=8,
        gpu_type=GPUChoices.K80,
    ),
    InstanceType(
        name="ml.p2.16xlarge",
        cpu=64,
        memory=732,
        price_per_hour=17.885,
        gpus=16,
        gpu_type=GPUChoices.K80,
    ),
    InstanceType(
        name="ml.g4dn.xlarge",
        cpu=4,
        memory=16,
        price_per_hour=0.822,
        gpus=1,
        gpu_type=GPUChoices.T4,
    ),
    InstanceType(
        name="ml.g4dn.2xlarge",
        cpu=8,
        memory=32,
        price_per_hour=1.047,
        gpus=1,
        gpu_type=GPUChoices.T4,
    ),
    InstanceType(
        name="ml.g4dn.4xlarge",
        cpu=16,
        memory=64,
        price_per_hour=1.678,
        gpus=1,
        gpu_type=GPUChoices.T4,
    ),
    InstanceType(
        name="ml.g4dn.12xlarge",
        cpu=48,
        memory=192,
        price_per_hour=5.453,
        gpus=4,
        gpu_type=GPUChoices.T4,
    ),
    InstanceType(
        name="ml.g4dn.16xlarge",
        cpu=64,
        memory=256,
        price_per_hour=6.066,
        gpus=1,
        gpu_type=GPUChoices.T4,
    ),
]


class ModelChoices(TextChoices):
    # The values must be short
    # The labels must be in the form "<app_label>-<model_name>"
    ALGORITHMS_JOB = "A", "algorithms-job"
    EVALUATION_EVALUATION = "E", "evaluation-evaluation"


class AmazonSageMakerBatchExecutor(Executor):
    IS_EVENT_DRIVEN = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__duration = None
        self.__stdout = []
        self.__stderr = []
        self.__runtime_metrics = {}

        self.__sagemaker_client = None
        self.__logs_client = None
        self.__cloudwatch_client = None

    @staticmethod
    def get_job_params(*, event):
        # TODO needs a test
        job_name = event["TransformJobName"]

        prefix_regex = re.escape(settings.COMPONENTS_REGISTRY_PREFIX)
        model_regex = r"|".join(ModelChoices.values)
        pattern = rf"^{prefix_regex}\-(?P<job_model>{model_regex})\-(?P<job_pk>{UUID4_REGEX})$"

        result = re.match(pattern, job_name)

        if result is None:
            raise ValueError("Invalid job name")
        else:
            job_model = ModelChoices(result.group("job_model")).label
            job_app_label, job_model_name = job_model.split("-")
            job_pk = result.group("job_pk")
            return job_app_label, job_model_name, job_pk

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
    def stdout(self):
        return "\n".join(self.__stdout)

    @property
    def stderr(self):
        return "\n".join(self.__stderr)

    @property
    def duration(self):
        return self.__duration

    @property
    def runtime_metrics(self):
        return self.__runtime_metrics

    @property
    def _invocation_prefix(self):
        # TODO test this is a different path to IO prefix
        return safe_join("/invocations", *self.job_path_parts)

    @property
    def _invocation_key(self):
        # TODO test this contains the pk, and must use the invocation prefix
        return safe_join(self._invocation_prefix, "invocation.json")

    @property
    def _transform_job_name(self):
        # TODO test this
        # SageMaker requires job names to be less than 63 chars
        job_name = f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self._job_id}"

        for value, label in ModelChoices.choices:
            job_name = job_name.replace(label, value)

        return job_name

    @property
    def _log_group_name(self):
        # Hardcoded by AWS
        return "/aws/sagemaker/TransformJobs"

    @property
    def _instance_type(self):
        """Find the cheapest instance that can run this job"""

        if self._requires_gpu:
            # For now only use single gpu, T4 instances
            n_gpu = 1
            gpu_type = GPUChoices.T4
        else:
            n_gpu = 0
            gpu_type = None

        compatible_instances = [
            instance
            for instance in INSTANCE_OPTIONS
            if instance.gpus == n_gpu
            and instance.gpu_type == gpu_type
            and instance.memory >= self._memory_limit
        ]

        if not compatible_instances:
            raise ValueError("No suitable instance types for job")

        # Get the lowest priced instance
        compatible_instances.sort(key=lambda x: x.price_per_hour)
        return compatible_instances[0].name

    def execute(self, *, input_civs, input_prefixes):
        self._create_invocation_json(
            input_civs=input_civs, input_prefixes=input_prefixes
        )
        self._create_transform_job()

    def deprovision(self):
        super().deprovision()
        # TODO cancel any running tasks
        self._delete_objects(
            bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            prefix=self._invocation_prefix,
        )
        self._delete_objects(
            bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            prefix=self._invocation_prefix,
        )

    def _create_invocation_json(self, *, input_civs, input_prefixes):
        f = io.BytesIO(
            json.dumps(
                self._get_invocation_json(
                    input_civs=input_civs, input_prefixes=input_prefixes
                )
            ).encode("utf-8")
        )
        self._s3_client.upload_fileobj(
            f, settings.COMPONENTS_INPUT_BUCKET_NAME, self._invocation_key
        )

    def _create_transform_job(self):
        self._sagemaker_client.create_transform_job(
            TransformJobName=self._transform_job_name,
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
                "InstanceType": self._instance_type,
                "InstanceCount": 1,
            },
            Environment={  # Up to 16 pairs
                "LOGLEVEL": "INFO",
            },
            ModelClientConfig={
                "InvocationsTimeoutInSeconds": self._time_limit,
                "InvocationsMaxRetries": 0,
            },
        )

    def handle_event(self, *, event):
        job_status = event["TransformJobStatus"]

        if job_status == "Completed":
            # TODO inspect return code
            self._set_duration(event=event)
            self._set_task_logs()
            self._set_runtime_metrics(event=event)
        elif job_status == "Failed":
            # TODO what about time limit exceeded?
            # This is an internal error to AWS, could be permissions
            # Needs investigating by a site administrator
            raise RuntimeError
        elif job_status == "Stopped":
            raise TaskCancelled
        else:
            raise ValueError("Invalid job status")

    def _set_duration(self, *, event):
        try:
            started = ms_timestamp_to_datetime(event["TransformStartTime"])
            stopped = ms_timestamp_to_datetime(event["TransformEndTime"])
            self.__duration = stopped - started
        except Exception as e:
            logger.warning(f"Could not determine duration: {e}")
            self.__duration = None

    def _get_log_stream_name(self):
        response = self._logs_client.describe_log_streams(
            logGroupName=self._log_group_name,
            logStreamNamePrefix=f"{self._transform_job_name}",
        )

        if "nextToken" in response:
            raise RuntimeError("Too many log streams found")

        log_streams = {
            s["logStreamName"]
            for s in response["logStreams"]
            if not s["logStreamName"].endswith("/data-log")
        }

        if len(log_streams) == 1:
            return log_streams.pop()
        else:
            raise RuntimeError("Log stream not found")

    def _set_task_logs(self):
        response = self._logs_client.get_log_events(
            logGroupName=self._log_group_name,
            logStreamName=self._get_log_stream_name(),
            limit=LOGLINES,
            startFromHead=False,
        )
        events = response["events"]

        stdout = []
        stderr = []

        for event in events:
            try:
                parsed_log = parse_structured_log(
                    log=event["message"].replace("\x00", "")
                )
                timestamp = ms_timestamp_to_datetime(event["timestamp"])
            except (JSONDecodeError, KeyError, ValueError):
                logger.error("Could not parse log")
                continue

            if parsed_log is not None:
                output = f"{timestamp.isoformat()} {parsed_log.message}"
                if parsed_log.source == SourceChoices.STDOUT:
                    stdout.append(output)
                elif parsed_log.source == SourceChoices.STDERR:
                    stderr.append(output)
                else:
                    logger.error("Invalid source")

        self.__stdout = stdout
        self.__stderr = stderr

    def _set_runtime_metrics(self, *, event):
        query_id = "q"

        start_time = ms_timestamp_to_datetime(event["TransformStartTime"])
        end_time = ms_timestamp_to_datetime(event["TransformEndTime"])
        query = f"SEARCH('{{{self._log_group_name},Host}} Host={self._transform_job_name}/i-', 'Average', 60)"

        response = self._cloudwatch_client.get_metric_data(
            MetricDataQueries=[{"Id": query_id, "Expression": query}],
            # Add buffer time to allow metrics to be delivered
            StartTime=start_time - timedelta(minutes=1),
            EndTime=end_time + timedelta(minutes=5),
        )

        if "NextToken" in response:
            raise logger.error("Too many metrics found")

        self.__runtime_metrics = {
            metric["Label"]: {
                "status": metric["StatusCode"],
                "timestamps": [t.isoformat() for t in metric["Timestamps"]],
                "values": metric["Values"],
            }
            for metric in response["MetricDataResults"]
            if metric["Id"] == query_id
        }
