import logging
from abc import ABC, abstractmethod
from typing import NamedTuple

import boto3
from django.conf import settings
from django.utils.functional import cached_property

from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.utils import ms_timestamp_to_datetime
from grandchallenge.components.schemas import GPUTypeChoices

logger = logging.getLogger(__name__)


class InstanceType(NamedTuple):
    name: str
    cpu: int
    memory: float
    usd_cents_per_hour_excluding_tax: int
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
        usd_cents_per_hour_excluding_tax=14,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.large",
        cpu=2,
        memory=16,
        usd_cents_per_hour_excluding_tax=18,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.xlarge",
        cpu=4,
        memory=32,
        usd_cents_per_hour_excluding_tax=36,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.2xlarge",
        cpu=8,
        memory=64,
        usd_cents_per_hour_excluding_tax=72,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.4xlarge",
        cpu=16,
        memory=128,
        usd_cents_per_hour_excluding_tax=143,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.8xlarge",
        cpu=32,
        memory=256,
        usd_cents_per_hour_excluding_tax=285,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.12xlarge",
        cpu=48,
        memory=384,
        usd_cents_per_hour_excluding_tax=426,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.16xlarge",
        cpu=64,
        memory=512,
        usd_cents_per_hour_excluding_tax=569,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.24xlarge",
        cpu=96,
        memory=768,
        usd_cents_per_hour_excluding_tax=853,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.r7i.48xlarge",
        cpu=192,
        memory=1536,
        usd_cents_per_hour_excluding_tax=1706,
        gpu_type=GPUTypeChoices.NO_GPU,
    ),
    InstanceType(
        name="ml.p4d.24xlarge",
        cpu=96,
        memory=1152,
        usd_cents_per_hour_excluding_tax=2728,
        gpus=8,
        gpu_type=GPUTypeChoices.A100,
        nvme_volume_size=8 * 1000,
    ),
    InstanceType(
        name="ml.p3.2xlarge",
        cpu=8,
        memory=61,
        usd_cents_per_hour_excluding_tax=414,
        gpus=1,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3.8xlarge",
        cpu=32,
        memory=244,
        usd_cents_per_hour_excluding_tax=1587,
        gpus=4,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3.16xlarge",
        cpu=64,
        memory=488,
        usd_cents_per_hour_excluding_tax=3041,
        gpus=8,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p3dn.24xlarge",
        cpu=96,
        memory=768,
        usd_cents_per_hour_excluding_tax=3877,
        gpus=8,
        gpu_type=GPUTypeChoices.V100,
    ),
    InstanceType(
        name="ml.p2.xlarge",
        cpu=4,
        memory=61,
        usd_cents_per_hour_excluding_tax=122,
        gpus=1,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.p2.8xlarge",
        cpu=32,
        memory=488,
        usd_cents_per_hour_excluding_tax=934,
        gpus=8,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.p2.16xlarge",
        cpu=64,
        memory=732,
        usd_cents_per_hour_excluding_tax=1789,
        gpus=16,
        gpu_type=GPUTypeChoices.K80,
    ),
    InstanceType(
        name="ml.g5.xlarge",
        cpu=4,
        memory=16,
        usd_cents_per_hour_excluding_tax=157,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=250,
    ),
    InstanceType(
        name="ml.g5.2xlarge",
        cpu=8,
        memory=32,
        usd_cents_per_hour_excluding_tax=169,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=450,
    ),
    InstanceType(
        name="ml.g5.4xlarge",
        cpu=16,
        memory=64,
        usd_cents_per_hour_excluding_tax=227,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=600,
    ),
    InstanceType(
        name="ml.g5.8xlarge",
        cpu=32,
        memory=128,
        usd_cents_per_hour_excluding_tax=342,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g5.12xlarge",
        cpu=48,
        memory=192,
        usd_cents_per_hour_excluding_tax=791,
        gpus=4,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=3800,
    ),
    InstanceType(
        name="ml.g5.16xlarge",
        cpu=64,
        memory=256,
        usd_cents_per_hour_excluding_tax=572,
        gpus=1,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=1900,
    ),
    InstanceType(
        name="ml.g5.24xlarge",
        cpu=96,
        memory=384,
        usd_cents_per_hour_excluding_tax=1136,
        gpus=4,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=3800,
    ),
    InstanceType(
        name="ml.g5.48xlarge",
        cpu=192,
        memory=768,
        usd_cents_per_hour_excluding_tax=2273,
        gpus=8,
        gpu_type=GPUTypeChoices.A10G,
        nvme_volume_size=2 * 3800,
    ),
    InstanceType(
        name="ml.g4dn.xlarge",
        cpu=4,
        memory=16,
        usd_cents_per_hour_excluding_tax=83,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=125,
    ),
    InstanceType(
        name="ml.g4dn.2xlarge",
        cpu=8,
        memory=32,
        usd_cents_per_hour_excluding_tax=105,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=225,
    ),
    InstanceType(
        name="ml.g4dn.4xlarge",
        cpu=16,
        memory=64,
        usd_cents_per_hour_excluding_tax=168,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=225,
    ),
    InstanceType(
        name="ml.g4dn.8xlarge",
        cpu=32,
        memory=128,
        usd_cents_per_hour_excluding_tax=304,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g4dn.12xlarge",
        cpu=48,
        memory=192,
        usd_cents_per_hour_excluding_tax=546,
        gpus=4,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
    InstanceType(
        name="ml.g4dn.16xlarge",
        cpu=64,
        memory=256,
        usd_cents_per_hour_excluding_tax=607,
        gpus=1,
        gpu_type=GPUTypeChoices.T4,
        nvme_volume_size=900,
    ),
]


class AmazonSageMakerBaseExecutor(Executor, ABC):
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
    def _create_job_boto(self):
        pass

    @abstractmethod
    def _stop_job_boto(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__utilization_duration = None

        self.__sagemaker_client = None
        self.__logs_client = None
        self.__cloudwatch_client = None

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
    def utilization_duration(self):
        return self.__utilization_duration

    @cached_property
    def _instance_type(self):
        """Find the cheapest instance that can run this job"""

        if self._requires_gpu_type == GPUTypeChoices.NO_GPU:
            n_gpu = 0
        else:
            n_gpu = 1

        compatible_instances = [
            instance
            for instance in INSTANCE_OPTIONS
            if instance.gpus >= n_gpu
            and instance.gpu_type == self._requires_gpu_type
            and instance.memory >= self._memory_limit
        ]

        if not compatible_instances:
            raise ValueError("No suitable instance types for job")

        # Get the lowest priced instance
        compatible_instances.sort(
            key=lambda x: x.usd_cents_per_hour_excluding_tax
        )
        return compatible_instances[0]

    @property
    def usd_cents_per_hour(self):
        return self._instance_type.usd_cents_per_hour_excluding_tax * (
            1 + settings.COMPONENTS_TAX_RATE
        )

    @property
    def _max_memory_mb(self):
        # Reserve 1 GB for the system
        return (self._instance_type.memory - 1) * 1024

    def _set_duration(self, *, event):
        try:
            started = ms_timestamp_to_datetime(
                self._get_start_time(event=event)
            )
            stopped = ms_timestamp_to_datetime(self._get_end_time(event=event))
            self.__utilization_duration = stopped - started
        except TypeError:
            logger.warning("Invalid start or end time, duration undetermined")
            self.__utilization_duration = None

    @abstractmethod
    def _handle_stopped_job(self, *, event):
        pass
