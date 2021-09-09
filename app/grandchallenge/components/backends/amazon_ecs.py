import json
import logging
import shutil
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path

import boto3
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.utils._os import safe_join
from panimg.image_builders import image_builder_mhd, image_builder_tiff

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    ComponentJobActive,
)
from grandchallenge.components.backends.utils import LOGLINES, user_error

logger = logging.getLogger(__name__)


class AmazonECSExecutor:
    def __init__(
        self,
        *,
        job_id: str,
        exec_image_sha256: str,
        exec_image_repo_tag: str,
        exec_image_file: File,
        memory_limit: int,
        requires_gpu: bool,
    ):
        self._job_id = job_id
        self._exec_image_sha256 = exec_image_sha256
        self._exec_image_repo_tag = exec_image_repo_tag
        self._exec_image_file = exec_image_file
        self._memory_limit = memory_limit
        self._requires_gpu = requires_gpu

        if self._memory_limit < 4 or self._memory_limit > 30:
            raise RuntimeError("AWS only supports 4g to 30g of memory")

        self.__batch_client = None
        self.__ecs_client = None
        self.__logs_client = None

    def provision(self, *, input_civs, input_prefixes):
        self._create_io_volumes()
        self._copy_input_files(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def execute(self):
        task_definition_arn = self._register_task_definition()
        self._run_task(task_definition_arn=task_definition_arn)

    def await_completion(self):
        job_summary = self._job_summary
        job_status = job_summary["status"]

        if job_status.casefold() == "SUCCEEDED".casefold():
            # Job was a success, continue
            return
        elif job_status.casefold() == "FAILED".casefold():
            exit_code = job_summary.get("container", {}).get("exitCode")
            if exit_code is None:
                raise RuntimeError(f"{self._job_id} did not start")
            elif int(exit_code) == 137:
                raise ComponentException(
                    "The container was killed as it exceeded the memory limit "
                    f"of {self._memory_limit}g."
                )
            elif int(exit_code) == 143:
                raise ComponentException("Time limit exceeded")
            else:
                # TODO Implement non-unified logging and use stderr
                raise ComponentException(user_error(self.stdout))
        else:
            raise ComponentJobActive(job_status)

    def get_outputs(self, *, output_interfaces):
        outputs = []

        with transaction.atomic():
            # Atomic block required as create_instance needs to
            # create interfaces in order to store the files
            for interface in output_interfaces:
                if interface.is_image_kind:
                    res = self._create_images_result(interface=interface)
                else:
                    res = self._create_file_result(interface=interface)

                outputs.append(res)

        return outputs

    def deprovision(self):
        # TODO - this should also cancel any running job
        shutil.rmtree(self._job_directory)
        self._deregister_job_definitions()

    @property
    def stdout(self):
        try:
            return "\n".join(self._job_last_attempt_unified_logs)
        except Exception as e:
            logger.warning(f"Could not fetch stdout: {e}")
            return ""

    @property
    def stderr(self):
        # TODO Implement non-unified logging
        return ""

    @property
    def duration(self):
        try:
            return self._job_last_attempt_duration
        except Exception as e:
            logger.warning(f"Could not determine duration: {e}")
            return None

    @property
    def _batch_client(self):
        if self.__batch_client is None:
            self.__batch_client = boto3.client("batch")
        return self.__batch_client

    @property
    def _ecs_client(self):
        if self.__ecs_client is None:
            self.__ecs_client = boto3.client("ecs")
        return self.__ecs_client

    @property
    def _logs_client(self):
        if self.__logs_client is None:
            self.__logs_client = boto3.client("logs")
        return self.__logs_client

    @property
    def _queue_arn(self):
        if self._requires_gpu:
            return settings.COMPONENTS_AWS_BATCH_GPU_QUEUE_ARN
        else:
            return settings.COMPONENTS_AWS_BATCH_CPU_QUEUE_ARN

    @property
    def _cluster_arn(self):
        if self._requires_gpu:
            return settings.COMPONENTS_AMAZON_ECS_GPU_CLUSTER_ARN
        else:
            return settings.COMPONENTS_AMAZON_ECS_CPU_CLUSTER_ARN

    @property
    def _log_group_name(self):
        if self._requires_gpu:
            return settings.COMPONENTS_AMAZON_ECS_GPU_LOG_GROUP_NAME
        else:
            return settings.COMPONENTS_AMAZON_ECS_CPU_LOG_GROUP_NAME

    @property
    def _job_summary(self):
        response = self._batch_client.list_jobs(
            jobQueue=self._queue_arn,
            filters=[{"name": "JOB_NAME", "values": [self._job_id]}],
        )

        job_summary_list = response["jobSummaryList"]

        if len(job_summary_list) != 1:
            raise RuntimeError(
                f"{len(job_summary_list)} job(s) found for with name {self._job_id}"
            )

        return job_summary_list[0]

    @property
    def _job_description(self):
        job_id = self._job_summary["jobId"]
        response = self._batch_client.describe_jobs(jobs=[job_id])

        job_descriptions = response["jobs"]

        if len(job_descriptions) != 1:
            raise RuntimeError(
                f"{len(job_descriptions)} job(s) found for with name {self._job_id}"
            )

        return job_descriptions[0]

    @property
    def _job_last_attempt_log_stream_name(self):
        return self._job_description["attempts"][-1]["container"][
            "logStreamName"
        ]

    @property
    def _job_last_attempt_unified_logs(self):
        response = self._logs_client.get_log_events(
            logGroupName="/aws/batch/job",
            logStreamName=self._job_last_attempt_log_stream_name,
            limit=LOGLINES,
            startFromHead=False,
        )
        events = response["events"]

        loglines = [
            # Match the format of the docker logs
            f"{self._timestamp_to_datetime(e['timestamp']).isoformat()} {e['message']}"
            for e in events
        ]

        return loglines

    @staticmethod
    def _timestamp_to_datetime(timestamp):
        """Convert AWS timestamps (ms from epoch) to datetime"""
        return datetime.fromtimestamp(timestamp * 0.001, tz=timezone.utc)

    @property
    def _job_last_attempt_duration(self):
        attempt_info = self._job_description["attempts"][-1]
        started_at = self._timestamp_to_datetime(attempt_info["startedAt"])
        stopped_at = self._timestamp_to_datetime(attempt_info["stoppedAt"])
        return stopped_at - started_at

    @property
    def _job_directory(self):
        dir_parts = self._job_id.split("-", 2)

        if len(dir_parts) != 3:
            raise ValueError(f"Invalid job id {self._job_id}")

        return (
            Path(settings.COMPONENTS_AMAZON_ECS_NFS_MOUNT_POINT)
            / dir_parts[0]
            / dir_parts[1]
            / dir_parts[2]
        ).resolve()

    @property
    def _input_directory(self):
        return self._job_directory / "input"

    @property
    def _output_directory(self):
        return self._job_directory / "output"

    def _create_io_volumes(self):
        self._job_directory.parent.parent.mkdir(exist_ok=True, parents=False)
        self._job_directory.parent.mkdir(exist_ok=True, parents=False)
        self._job_directory.mkdir(exist_ok=False, parents=False)
        self._input_directory.mkdir(exist_ok=False, parents=False)
        self._output_directory.mkdir(exist_ok=False, parents=False)

    def _copy_input_files(self, *, input_civs, input_prefixes):
        for civ in input_civs:
            prefix = self._input_directory

            if str(civ.pk) in input_prefixes:
                # TODO
                raise NotImplementedError

            if civ.decompress:
                # TODO
                raise NotImplementedError
            else:
                dest = Path(safe_join(prefix, civ.relative_path))

            # We know that the dest is within the prefix as
            # safe_join is used, so ok to create the parents here
            dest.parent.mkdir(exist_ok=True, parents=True)

            with civ.input_file.open("rb") as fs, open(dest, "wb") as fd:
                for chunk in fs.chunks():
                    fd.write(chunk)

    @property
    def _resource_requirements(self):
        if self._requires_gpu:
            return [{"type": "GPU", "value": "1"}]
        else:
            return []

    @property
    def _required_memory_units(self):
        return 1024 * self._memory_limit

    @property
    def _required_cpu_units(self):
        return 4096 if self._memory_limit > 16 else 2048

    @property
    def _container_definitions(self):
        container_definitions = [
            {
                # Add a second essential container that kills the task
                # once the time limit is reached.
                # See https://github.com/aws/containers-roadmap/issues/572
                "command": ["sleep", str(settings.CELERY_TASK_TIME_LIMIT)],
                "image": settings.COMPONENTS_IO_IMAGE,
                "name": f"{self._job_id}-timeout",
            },
            {
                "command": [
                    # TODO remove setting command
                    "curl",
                    "-I",
                    "https://www.google.com",
                ],
                "cpu": self._required_cpu_units,
                "image": self._exec_image_repo_tag,
                "memory": self._required_memory_units,
                # TODO uncomment
                # "mountPoints": [
                #     {
                #         "containerPath": "/input",
                #         "sourceVolume": f"{self._job_id}-input",
                #         "readOnly": True,
                #     },
                #     {
                #         "containerPath": "/output",
                #         "sourceVolume": f"{self._job_id}-output",
                #         "readOnly": False,
                #     },
                # ],
                "name": self._job_id,
                "resourceRequirements": self._resource_requirements,
            },
        ]

        for c in container_definitions:
            c.update(
                {
                    "disableNetworking": True,
                    "dockerSecurityOptions": ["no-new-privileges"],
                    "essential": True,  # all essential for timeout to work
                    "linuxParameters": {
                        "capabilities": {"drop": ["ALL"]},
                        "initProcessEnabled": True,
                        "maxSwap": 0,
                        "swappiness": 0,
                    },
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": self._log_group_name,
                            "awslogs-region": settings.COMPONENTS_AMAZON_ECS_LOGS_REGION,
                            "awslogs-stream-prefix": "ecs",
                        },
                    },
                    "privileged": False,
                    "ulimits": [
                        {
                            "name": "nproc",
                            "hardLimit": settings.COMPONENTS_PIDS_LIMIT,
                            "softLimit": settings.COMPONENTS_PIDS_LIMIT,
                        }
                    ],
                    "user": "nobody",
                }
            )

        return container_definitions

    def _register_task_definition(self):
        response = self._ecs_client.register_task_definition(
            containerDefinitions=self._container_definitions,
            cpu=str(self._required_cpu_units),
            family=self._job_id,
            ipcMode="none",
            memory=str(self._required_memory_units),
            networkMode="none",
            requiresCompatibilities=["EC2"],
            # TODO placement constrains for GPU?
            # TODO set tags
            # TODO uncomment
            # volumes=[
            #     {
            #         "name": f"{self._job_id}-input",
            #         "host": {"sourcePath": str(self._input_directory)},
            #     },
            #     {
            #         "name": f"{self._job_id}-output",
            #         "host": {"sourcePath": str(self._output_directory)},
            #     },
            # ],
        )
        # TODO remove print statement
        print(response)
        return response["taskDefinition"]["taskDefinitionArn"]

    """
    >>> from grandchallenge.components.backends.amazon_ecs import AmazonECSExecutor
    >>> from django.utils.timezone import now
    >>> e = AmazonECSExecutor(job_id=f"test-{now().strftime('%H%M%S')}", exec_image_sha256="", exec_image_repo_tag="amazonlinux:2", exec_image_file=None, memory_limit=4, requires_gpu=False)
    >>> t = e._register_task_definition()
    >>> e._run_task(task_definition_arn=t)
    """

    def _run_task(self, *, task_definition_arn):
        response = self.__ecs_client.run_task(
            cluster=self._cluster_arn,
            count=1,
            enableExecuteCommand=False,
            enableECSManagedTags=True,
            propagateTags="TASK_DEFINITION",
            referenceId=self._job_id,
            taskDefinition=task_definition_arn,
        )
        # TODO remove print statement
        print(response)

    def _deregister_job_definitions(self):
        response = self._batch_client.describe_job_definitions(
            jobDefinitionName=self._job_id,
        )
        next_token = response.get("nextToken")

        for job_definition in response["jobDefinitions"]:
            self._batch_client.deregister_job_definition(
                jobDefinition=job_definition["jobDefinitionArn"],
            )

        if next_token:
            self._deregister_job_definitions()

    def _create_images_result(self, *, interface):
        base_dir = Path(
            safe_join(self._output_directory, interface.relative_path)
        )
        output_files = [f for f in base_dir.glob("*") if f.is_file()]

        if not output_files:
            raise ComponentException(f"{interface.relative_path} is empty")

        importer_result = import_images(
            input_directory=base_dir,
            builders=[image_builder_mhd, image_builder_tiff],
            recurse_subdirectories=False,
        )

        if len(importer_result.new_images) == 0:
            raise ComponentException(
                f"No images imported from {interface.relative_path}"
            )
        elif len(importer_result.new_images) > 1:
            raise ComponentException(
                f"Only 1 image should be produced in {interface.relative_path}, "
                f"we found {len(importer_result.new_images)}"
            )

        try:
            civ = interface.create_instance(
                image=next(iter(importer_result.new_images))
            )
        except ValidationError:
            raise ComponentException(
                f"The image produced in {interface.relative_path} is not valid"
            )

        return civ

    def _create_file_result(self, *, interface):
        output_file = Path(
            safe_join(self._output_directory, interface.relative_path)
        )

        if (
            output_file.is_symlink()
            or not output_file.is_file()
            or not output_file.exists()
        ):
            raise ComponentException(
                f"File {interface.relative_path} was not produced"
            )

        try:
            with open(output_file, "rb") as f:
                result = json.loads(
                    f.read().decode("utf-8"),
                    parse_constant=lambda x: None,  # Removes -inf, inf and NaN
                )
        except JSONDecodeError:
            raise ComponentException(
                f"The file produced at {interface.relative_path} is not valid json"
            )

        try:
            civ = interface.create_instance(value=result)
        except ValidationError:
            raise ComponentException(
                f"The file produced at {interface.relative_path} is not valid"
            )

        return civ
