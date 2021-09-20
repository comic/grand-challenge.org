import json
import logging
import shutil
from datetime import datetime, timezone
from enum import Enum
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
    RetryStep,
)
from grandchallenge.components.backends.utils import LOGLINES, user_error

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


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

        self.__ecs_client = None
        self.__logs_client = None

    def provision(self, *, input_civs, input_prefixes):
        self._create_io_volumes()
        self._copy_input_files(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def execute(self):
        if not self._list_task_arns(desired_status=TaskStatus.RUNNING):
            try:
                task_definition_arn = self._register_task_definition()
                self._run_task(task_definition_arn=task_definition_arn)
            except self._ecs_client.exceptions.ThrottlingException as e:
                raise RetryStep("Requests throttled") from e
            except self._ecs_client.exceptions.ClientException as e:
                if (
                    e.response["Error"]["Message"]
                    == "Tasks provisioning capacity limit exceeded."
                ):
                    raise RetryStep("Capacity Limit Exceeded") from e
                else:
                    raise
        else:
            logger.warning("A task is already running for this job")

    def await_completion(self):
        task_description = self._latest_task_description
        last_status = task_description["lastStatus"]

        if last_status == TaskStatus.STOPPED.value:
            # TODO Handle jobs killed by spot instance loss

            if task_description["stopCode"] == "TaskFailedToStart":
                self.execute()
                raise RetryStep("Job re-queued")

            container_exit_codes = {
                c["name"]: int(c["exitCode"])
                for c in task_description["containers"]
            }

            if container_exit_codes[self._main_container_name] == 0:
                # Job's a good un
                return
            elif container_exit_codes[self._main_container_name] == 137:
                raise ComponentException(
                    "The container was killed as it exceeded the memory limit "
                    f"of {self._memory_limit}g."
                )
            elif container_exit_codes[self._timeout_container_name] == 0:
                raise ComponentException("Time limit exceeded")
            else:
                raise ComponentException(user_error(self.stderr))
        else:
            raise RetryStep(f"Job active: {last_status}")

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
        try:
            shutil.rmtree(self._job_directory)
        except FileNotFoundError:
            logger.warning(
                f"Directory not found when trying to remove it: {self._job_directory}"
            )

        self._stop_running_tasks()
        self._deregister_task_definitions()

    @property
    def stdout(self):
        try:
            return "\n".join(self._get_task_logs(source="stdout"))
        except Exception as e:
            logger.warning(f"Could not fetch stdout: {e}")
            return ""

    @property
    def stderr(self):
        try:
            return "\n".join(self._get_task_logs(source="stderr"))
        except Exception as e:
            logger.warning(f"Could not fetch stdout: {e}")
            return ""

    @property
    def duration(self):
        try:
            return self._latest_task_duration
        except Exception as e:
            logger.warning(f"Could not determine duration: {e}")
            return None

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
    def _log_stream_prefix(self):
        return "ecs"

    @property
    def _main_container_name(self):
        return self._job_id

    @property
    def _timeout_container_name(self):
        return f"{self._main_container_name}-timeout"

    @property
    def _latest_task_description(self):
        # On ECS the tasks can only have a desiredStatus of RUNNING or
        # STOPPED, so look for the running tasks first, and if nothing is
        # found, it should have a desired status of STOPPED
        task_arns = self._list_task_arns(desired_status=TaskStatus.RUNNING)
        task_arns += self._list_task_arns(desired_status=TaskStatus.STOPPED)
        task_descriptions = self._list_task_descriptions(task_arns=task_arns)

        task_descriptions.sort(key=lambda x: x["createdAt"], reverse=True)

        return task_descriptions[0]

    def _get_task_logs(self, *, source):
        response = self._logs_client.get_log_events(
            logGroupName=self._log_group_name,
            logStreamName=f"{self._log_stream_prefix}/{self._main_container_name}",
            limit=LOGLINES,
            startFromHead=False,
        )
        events = response["events"]

        loglines = []

        for event in events:
            message = json.loads(event["message"])

            if message["source"] == source:
                timestamp = self._timestamp_to_datetime(event["timestamp"])
                log = message["log"].replace("\x00", "")
                loglines.append(f"{timestamp.isoformat()} {log}")

        return loglines

    @staticmethod
    def _timestamp_to_datetime(timestamp):
        """Convert AWS timestamps (ms from epoch) to datetime"""
        return datetime.fromtimestamp(timestamp * 0.001, tz=timezone.utc)

    @property
    def _latest_task_duration(self):
        task_description = self._latest_task_description
        return task_description["stoppedAt"] - task_description["startedAt"]

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
                "command": ["sleep", "7200"],  # TODO customize timeout
                "image": "public.ecr.aws/amazonlinux/amazonlinux:2",
                "name": self._timeout_container_name,
            },
            {
                "cpu": self._required_cpu_units,
                "image": self._exec_image_repo_tag,
                "memory": self._required_memory_units,
                "mountPoints": [
                    {
                        "containerPath": "/input",
                        "sourceVolume": f"{self._job_id}-input",
                        "readOnly": True,
                    },
                    {
                        "containerPath": "/output",
                        "sourceVolume": f"{self._job_id}-output",
                        "readOnly": False,
                    },
                ],
                "name": self._main_container_name,
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
                        "logDriver": "fluentd",
                        "options": {
                            "fluentd-address": "unix:///tmp/fluent-bit/sock",
                            "tag": f"/{c['name']}",
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
                }
            )

        return container_definitions

    def _register_task_definition(self):
        response = self._ecs_client.register_task_definition(
            containerDefinitions=self._container_definitions,
            cpu=str(self._required_cpu_units),
            family=self._job_id,
            memory=str(self._required_memory_units),
            networkMode="none",
            requiresCompatibilities=["EC2"],
            # TODO set tags
            volumes=[
                {
                    "name": f"{self._job_id}-input",
                    "host": {"sourcePath": str(self._input_directory)},
                },
                {
                    "name": f"{self._job_id}-output",
                    "host": {"sourcePath": str(self._output_directory)},
                },
            ],
        )
        return response["taskDefinition"]["taskDefinitionArn"]

    def _run_task(self, *, task_definition_arn):
        self._ecs_client.run_task(
            cluster=self._cluster_arn,
            count=1,
            enableExecuteCommand=False,
            enableECSManagedTags=True,
            group=self._log_group_name,
            placementConstraints=[{"type": "distinctInstance"}],
            propagateTags="TASK_DEFINITION",
            referenceId=self._job_id,
            taskDefinition=task_definition_arn,
        )

    def _list_task_arns(
        self, *, desired_status, next_token="", task_arns=None
    ):
        if task_arns is None:
            task_arns = []

        response = self._ecs_client.list_tasks(
            cluster=self._cluster_arn,
            family=self._job_id,
            desiredStatus=desired_status.value,
            nextToken=next_token,
        )

        task_arns += response["taskArns"]

        if "nextToken" in response:
            return self._list_task_arns(
                desired_status=desired_status,
                next_token=response["nextToken"],
                task_arns=task_arns,
            )

        return task_arns

    def _list_task_descriptions(self, *, task_arns, task_descriptions=None):
        if task_descriptions is None:
            task_descriptions = []

        limit = 100  # Defined by AWS

        response = self._ecs_client.describe_tasks(
            tasks=task_arns[:limit], cluster=self._cluster_arn
        )

        task_descriptions += response["tasks"]

        if len(task_arns) > limit:
            return self._list_task_descriptions(
                task_arns=task_arns[limit:],
                task_descriptions=task_descriptions,
            )

        return task_descriptions

    def _stop_running_tasks(self):
        """Stop all the running tasks for this job"""
        task_arns = self._list_task_arns(desired_status=TaskStatus.RUNNING)

        for task_arn in task_arns:
            self._ecs_client.stop_task(
                cluster=self._cluster_arn, task=task_arn,
            )

    def _deregister_task_definitions(self):
        response = self._ecs_client.list_task_definitions(
            familyPrefix=self._job_id, status="ACTIVE"
        )
        next_token = response.get("nextToken")

        for task_definition_arn in response["taskDefinitionArns"]:
            self._ecs_client.deregister_task_definition(
                taskDefinition=task_definition_arn,
            )

        if next_token:
            self._deregister_task_definitions()

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
