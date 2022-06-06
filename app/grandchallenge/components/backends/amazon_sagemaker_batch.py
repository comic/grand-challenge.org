import io
import json
import logging
import re
from json import JSONDecodeError

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
        # TODO
        raise NotImplementedError

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

    def execute(self, *, input_civs, input_prefixes):
        self._create_invocation_json(
            input_civs=input_civs, input_prefixes=input_prefixes
        )
        self._create_transform_job()

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
                # TODO get instance type
                "InstanceType": "ml.g4dn.xlarge",
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
            self._set_duration(event=event)
            self._set_task_logs()
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
            started = ms_timestamp_to_datetime(
                event["TransformStartTime"]
                if "TransformStartTime" in event
                else event["CreationTime"]
            )
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
