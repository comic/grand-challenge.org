import io
import json
import logging
import re

import boto3
from django.conf import settings
from django.db.models import TextChoices
from django.utils._os import safe_join

from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.utils import get_sagemaker_model_name

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
        # TODO
        return ""

    @property
    def stderr(self):
        # TODO
        return ""

    @property
    def duration(self):
        # TODO
        raise NotImplementedError

    @property
    def runtime_metrics(self):
        # TODO
        raise NotImplementedError

    @property
    def invocation_prefix(self):
        # TODO test this is a different path to IO prefix
        return safe_join("/invocations", *self.job_path_parts)

    @property
    def invocation_key(self):
        # TODO test this contains the pk, and must use the invocation prefix
        return safe_join(self.invocation_prefix, "invocation.json")

    @property
    def transform_job_name(self):
        # TODO test this
        # SageMaker requires job names to be less than 63 chars
        job_name = f"{settings.COMPONENTS_REGISTRY_PREFIX}-{self._job_id}"

        for value, label in ModelChoices.choices:
            job_name = job_name.replace(label, value)

        return job_name

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
            f, settings.COMPONENTS_INPUT_BUCKET_NAME, self.invocation_key
        )

    def _create_transform_job(self):
        self._sagemaker_client.create_transform_job(
            TransformJobName=self.transform_job_name,
            ModelName=get_sagemaker_model_name(
                repo_tag=self._exec_image_repo_tag
            ),
            TransformInput={
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self.invocation_key}",
                    }
                }
            },
            TransformOutput={
                "S3OutputPath": f"s3://{settings.COMPONENTS_OUTPUT_BUCKET_NAME}/{self.invocation_prefix}"
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
        # TODO
        raise NotImplementedError
