import boto3

from grandchallenge.components.backends.base import Executor


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
            self.__sagemaker_client = boto3.client("sagemaker")
        return self.__sagemaker_client

    @property
    def _logs_client(self):
        if self.__logs_client is None:
            self.__logs_client = boto3.client("logs")
        return self.__logs_client

    @property
    def _cloudwatch_client(self):
        if self.__cloudwatch_client is None:
            self.__cloudwatch_client = boto3.client("cloudwatch")
        return self.__cloudwatch_client

    @property
    def stdout(self):
        # TODO
        raise NotImplementedError

    @property
    def stderr(self):
        # TODO
        raise NotImplementedError

    @property
    def duration(self):
        # TODO
        raise NotImplementedError

    @property
    def runtime_metrics(self):
        # TODO
        raise NotImplementedError

    def execute(self, *, input_civs, input_prefixes):
        # TODO
        raise NotImplementedError

    def handle_event(self, *, event):
        # TODO
        raise NotImplementedError
