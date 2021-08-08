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


class AWSBatchExecutor:
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
        self.__logs_client = None

    def provision(self, *, input_civs, input_prefixes):
        self._create_io_volumes()
        self._copy_input_files(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def execute(self):
        job_definition_arn = self._register_job_definition()
        self._submit_job(job_definition_arn=job_definition_arn)

    def await_completion(self):
        job_summary = self._job_summary
        job_status = job_summary["status"]

        if job_status.casefold() == "SUCCEEDED".casefold():
            # Job was a success, continue
            return
        elif job_status.casefold() == "FAILED".casefold():
            exit_code = int(job_summary["container"]["exitCode"])
            if exit_code == 137:
                raise ComponentException(
                    "The container was killed as it exceeded the memory limit "
                    f"of {self._memory_limit}g."
                )
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
            Path(settings.COMPONENTS_AWS_BATCH_NFS_MOUNT_POINT)
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
        requirements = [
            # boto requires strings rather than ints
            {"type": "MEMORY", "value": str(1024 * self._memory_limit)},
            {
                "type": "VCPU",
                "value": str(4 if self._memory_limit > 16 else 2),
            },
        ]
        if self._requires_gpu:
            requirements.append({"type": "GPU", "value": "1"})
        return requirements

    def _register_job_definition(self):
        response = self._batch_client.register_job_definition(
            jobDefinitionName=self._job_id,
            type="container",
            containerProperties={
                # AWS batch does not appear to support dockerSecurityOptions,
                # so security_opt, cap_drop are not set. However, the batch
                # instances are heavily locked down.
                # Also no way to set network_disabled, cpu_period, cpu_quota,
                # cpu_shares, cpuset_cpus or runtime on batch
                "image": self._exec_image_repo_tag,
                "resourceRequirements": self._resource_requirements,
                "linuxParameters": {
                    # TODO devices,
                    "initProcessEnabled": True,
                    "maxSwap": 0,
                    "swappiness": 0,
                },
                "ulimits": [
                    {
                        "name": "nproc",
                        "hardLimit": settings.COMPONENTS_PIDS_LIMIT,
                        "softLimit": settings.COMPONENTS_PIDS_LIMIT,
                    }
                ],
                "privileged": False,
                "user": "nobody",
            },
            timeout={
                "attemptDurationSeconds": settings.CELERY_TASK_TIME_LIMIT
            },
            platformCapabilities=["EC2"],
            propagateTags=True,
        )
        return response["jobDefinitionArn"]

    def _submit_job(self, *, job_definition_arn):
        self._batch_client.submit_job(
            jobName=self._job_id,
            jobQueue=self._queue_arn,
            jobDefinition=job_definition_arn,
        )

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
