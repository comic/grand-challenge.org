import logging

import boto3
import botocore
from django.conf import settings

from grandchallenge.components.backends.base import Executor

logger = logging.getLogger(__name__)


class AmazonSageMakerBatchExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__sagemaker_client = None
        self.__logs_client = None
        self.__cloudwatch_client = None

    @staticmethod
    def get_job_params(*, event):
        # TODO
        raise NotImplementedError

    @property
    def _sagemaker_client(self):
        if self.__sagemaker_client is None:
            self.__sagemaker_client = boto3.client(
                "sagemaker",
                region_name=settings.COMPONENTS_AMAZON_SAGEMAKER_REGION,
            )
        return self.__sagemaker_client

    @property
    def _logs_client(self):
        if self.__logs_client is None:
            self.__logs_client = boto3.client(
                "logs", region_name=settings.COMPONENTS_AMAZON_SAGEMAKER_REGION
            )
        return self.__logs_client

    @property
    def _cloudwatch_client(self):
        if self.__cloudwatch_client is None:
            self.__cloudwatch_client = boto3.client(
                "cloudwatch",
                region_name=settings.COMPONENTS_AMAZON_SAGEMAKER_REGION,
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
    def _model_name(self):
        """
        The SageMaker model name

        These are quite restrictive, so we cannot use the container image name.
        They must be max 63 chars and match ^[a-zA-Z0-9]([-a-zA-Z0-9]*[a-zA-Z0-9])?$
        """
        model_name = self._exec_image_repo_tag

        # Assuming the registry prefix follows the recommendation of
        # organisation-project-env
        model_name_replacements = {
            f"{settings.COMPONENTS_REGISTRY_URL}/": "",
            "algorithms/algorithmimage": "A",
            "evaluation/method": "M",
            ":": "-",
            "/": "-",
            ".": "-",
        }

        for k, v in model_name_replacements.items():
            model_name = model_name.replace(k, v)

        return model_name

    def provision(self, *, input_civs, input_prefixes):
        super().provision(input_civs=input_civs, input_prefixes=input_prefixes)
        self._create_model()

    def execute(self, *, input_civs, input_prefixes):
        # TODO
        raise NotImplementedError

    def handle_event(self, *, event):
        # TODO
        raise NotImplementedError

    def _create_model(self):
        try:
            self._sagemaker_client.create_model(
                ModelName=self._model_name,
                PrimaryContainer={"Image": self._exec_image_repo_tag},
                ExecutionRoleArn=settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN,
                EnableNetworkIsolation=False,  # Restricted by VPC
                VpcConfig={
                    "SecurityGroupIds": [
                        settings.COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID,
                    ],
                    "Subnets": settings.COMPONENTS_AMAZON_SAGEMAKER_SUBNETS,
                },
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"][
                "Code"
            ] == "ValidationException" and error.response["Error"][
                "Message"
            ].startswith(
                "Cannot create already existing model"
            ):
                logger.info("SageMaker model already exists")
                # TODO - ensure that the config is up to date, maybe recreate the model?
            else:
                raise
