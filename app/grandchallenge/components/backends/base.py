import asyncio
import functools
import io
import json
import logging
import os
from abc import ABC, abstractmethod
from json import JSONDecodeError
from math import ceil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import NamedTuple
from uuid import UUID

import aioboto3
import boto3
import botocore
from asgiref.sync import async_to_sync
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.db import transaction
from django.utils._os import safe_join
from django.utils.functional import cached_property
from panimg.image_builders import image_builder_mhd, image_builder_tiff

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    UncleanExit,
)
from grandchallenge.components.backends.utils import user_error
from grandchallenge.components.models import (
    ComponentInterface,
    ComponentInterfaceValue,
    InterfaceKindChoices,
)
from grandchallenge.components.schemas import GPUTypeChoices
from grandchallenge.components.serializers import (
    ComponentInterfaceValueSerializer,
)
from grandchallenge.core.utils.error_messages import (
    format_validation_error_message,
)

logger = logging.getLogger(__name__)

MAX_SPOOL_SIZE = 1_000_000_000  # 1GB

CONCURRENCY = 50
ASYNC_BOTO_CONFIG = Config(max_pool_connections=120)


class JobParams(NamedTuple):
    app_label: str
    model_name: str
    pk: UUID
    attempt: int


class CIVProvisioningTask(NamedTuple):
    key: str
    task: functools.partial


def duration_to_millicents(*, duration, usd_cents_per_hour):
    return ceil(
        (duration.total_seconds() / 3600)
        * usd_cents_per_hour
        * 1000
        * settings.COMPONENTS_USD_TO_EUR
    )


def list_and_delete_objects_from_prefix(*, s3_client, bucket, prefix):
    if not (
        prefix.startswith("/io/")
        or prefix.startswith("/invocations/")
        or prefix.startswith("/training-outputs/")
        or prefix.startswith("/auxiliary-data/")
        or prefix.startswith("inputs/")
    ) or bucket not in {
        settings.COMPONENTS_OUTPUT_BUCKET_NAME,
        settings.COMPONENTS_INPUT_BUCKET_NAME,
        settings.AWS_HEALTH_IMAGING_BUCKET_NAME,
    }:
        # Guard against deleting something unexpected
        raise RuntimeError(
            "Deleting from this prefix or bucket is not allowed"
        )

    paginator = s3_client.get_paginator("list_objects_v2")

    page_iterator = paginator.paginate(
        Bucket=bucket,
        Prefix=(prefix.lstrip("/") if settings.USING_MINIO else prefix),
    )

    all_errors = []
    total_deleted = 0

    for page in page_iterator:
        if contents := page.get("Contents"):
            # AWS delete_objects API has a hard limit of 1000 objects per request
            # The list_objects_v2 paginator returns max 1000 objects per page by default,
            # so this should always fit within the delete_objects limit
            response = s3_client.delete_objects(
                Bucket=bucket,
                Delete={
                    "Objects": [
                        {"Key": content["Key"]} for content in contents
                    ],
                },
            )

            deleted_count = len(response.get("Deleted", []))
            total_deleted += deleted_count
            logger.debug(f"Deleted {deleted_count} objects from {bucket}")

            if errors := response.get("Errors"):
                all_errors.extend(errors)

    if total_deleted == 0:
        logger.debug(f"No objects found in {bucket}/{prefix}")
    else:
        logger.debug(
            f"Total deleted: {total_deleted} objects from {bucket}/{prefix}"
        )

    if all_errors:
        logger.error(
            f"Errors occurred while deleting: {len(all_errors)} failed deletions"
        )


async def s3_copy(
    *,
    source_bucket,
    source_key,
    target_bucket,
    target_key,
    semaphore,
    s3_client,
):
    async with semaphore:
        await s3_client.copy(
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Bucket=target_bucket,
            Key=target_key,
        )


async def s3_upload_content(*, content, bucket, key, semaphore, s3_client):
    async with semaphore:
        with io.BytesIO() as f:
            f.write(content)
            f.seek(0)

            await s3_client.upload_fileobj(
                Fileobj=f,
                Bucket=bucket,
                Key=key,
            )


class Executor(ABC):
    def __init__(
        self,
        *args,
        job_id: str,
        exec_image_repo_tag: str,
        memory_limit: int,
        time_limit: int,
        requires_gpu_type: GPUTypeChoices,
        use_warm_pool: bool,
        algorithm_model=None,
        ground_truth=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._job_id = job_id
        self._exec_image_repo_tag = exec_image_repo_tag
        self._memory_limit = memory_limit
        self._time_limit = time_limit
        self._requires_gpu_type = requires_gpu_type
        self._use_warm_pool = (
            use_warm_pool and settings.COMPONENTS_USE_WARM_POOL
        )
        self._stdout = []
        self._stderr = []
        self.__s3_client = None
        self._algorithm_model = algorithm_model
        self._ground_truth = ground_truth

    def provision(self, *, input_civs, input_prefixes):
        # We cannot run everything async as it requires database access.
        # So first we gather the async tasks that need to be run,
        # then execute them in the event loop for the current thread
        # using a method wrapped in @async_to_sync.
        provisioning_tasks = self._get_provisioning_tasks(
            input_civs=input_civs, input_prefixes=input_prefixes
        )
        self._provision(tasks=provisioning_tasks)

    @abstractmethod
    def execute(self): ...

    @abstractmethod
    def handle_event(self, *, event): ...

    def get_outputs(self, *, output_interfaces):
        """Create ComponentInterfaceValues from the output interfaces"""
        outputs = []

        with transaction.atomic():
            # Atomic block required as create_instance needs to
            # create interfaces in order to store the files
            for interface in output_interfaces:
                if interface.is_image_kind:
                    res = self._create_images_result(interface=interface)
                elif interface.is_json_kind:
                    res = self._create_json_result(interface=interface)
                else:
                    res = self._create_file_result(interface=interface)

                outputs.append(res)

        return outputs

    def deprovision(self):
        self._delete_objects(
            bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            prefix=self._io_prefix,
        )
        self._delete_objects(
            bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            prefix=self._io_prefix,
        )
        self._delete_objects(
            bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            prefix=self._auxiliary_data_prefix,
        )

    @staticmethod
    @abstractmethod
    def get_job_name(*, event):
        pass

    @staticmethod
    @abstractmethod
    def get_job_params(*, job_name): ...

    @property
    def stdout(self):
        return "\n".join(self._stdout)

    @property
    def stderr(self):
        return "\n".join(self._stderr)

    @property
    @abstractmethod
    def duration(self): ...

    @property
    @abstractmethod
    def usd_cents_per_hour(self): ...

    @property
    @abstractmethod
    def runtime_metrics(self): ...

    @property
    @abstractmethod
    def external_admin_url(self): ...

    @property
    @abstractmethod
    def warm_pool_retained_billable_time_in_seconds(self): ...

    @property
    def invocation_environment(self):
        env = {  # Up to 16 pairs
            "LOG_LEVEL": "INFO",
            "PYTHONUNBUFFERED": "1",
            "no_proxy": "amazonaws.com",
            "GRAND_CHALLENGE_COMPONENT_WRITABLE_DIRECTORIES": "/opt/ml/output/data:/opt/ml/model:/opt/ml/input/data/ground_truth:/opt/ml/checkpoints:/tmp",
            "GRAND_CHALLENGE_COMPONENT_POST_CLEAN_DIRECTORIES": "/opt/ml/output/data:/opt/ml/model:/opt/ml/input/data/ground_truth",
            "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": str(
                self._max_memory_mb
            ),
        }
        if self._algorithm_model:
            env["GRAND_CHALLENGE_COMPONENT_MODEL"] = (
                f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self._algorithm_model_key}"
            )
        if self._ground_truth:
            env["GRAND_CHALLENGE_COMPONENT_GROUND_TRUTH"] = (
                f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self._ground_truth_key}"
            )
        return env

    @property
    def _max_memory_mb(self):
        return self._memory_limit * 1024

    @property
    def compute_cost_euro_millicents(self):
        duration = self.duration
        if duration is None:
            return None
        else:
            return duration_to_millicents(
                duration=duration, usd_cents_per_hour=self.usd_cents_per_hour
            )

    @property
    def job_path_parts(self):
        path_parts = self._job_id.split("-", 2)

        if len(path_parts) != 3 or "/" in self._job_id or "." in self._job_id:
            raise ValueError(f"Invalid job id {self._job_id}")

        return path_parts

    @property
    def _io_prefix(self):
        return safe_join("/io", *self.job_path_parts)

    @property
    def _invocation_prefix(self):
        return safe_join("/invocations", *self.job_path_parts)

    @property
    def _invocation_key(self):
        return safe_join(self._invocation_prefix, "invocation.json")

    @property
    def _result_key(self):
        return safe_join(
            self._io_prefix, ".sagemaker_shim", "inference_result.json"
        )

    @property
    def _s3_client(self):
        if self.__s3_client is None:
            self.__s3_client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            )
        return self.__s3_client

    @property
    def _auxiliary_data_prefix(self):
        return safe_join("/auxiliary-data", *self.job_path_parts)

    @property
    def _algorithm_model_key(self):
        return safe_join(self._auxiliary_data_prefix, "algorithm-model.tar.gz")

    @property
    def _ground_truth_key(self):
        return safe_join(self._auxiliary_data_prefix, "ground-truth.tar.gz")

    @property
    def _required_volume_size_gb(self):
        return max(
            # Factor 3 for decompression and making copies
            ceil(3 * self._input_size_bytes / settings.GIGABYTE),
            # Or match what was provided with Batch Inference
            30,
        )

    @cached_property
    def _input_size_bytes(self):
        inputs_size_bytes = self._get_input_prefix_size_bytes(
            prefix=self._io_prefix
        )
        auxiliary_size_bytes = self._get_input_prefix_size_bytes(
            prefix=self._auxiliary_data_prefix
        )

        return inputs_size_bytes + auxiliary_size_bytes

    def _get_input_prefix_size_bytes(self, *, prefix):
        paginator = self._s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME, Prefix=prefix
        )

        total_size = 0

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    total_size += obj["Size"]

        return total_size

    @async_to_sync
    async def _provision(self, *, tasks):
        semaphore = asyncio.Semaphore(CONCURRENCY)
        session = aioboto3.Session()

        async with session.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            config=ASYNC_BOTO_CONFIG,
        ) as s3_client:
            async with asyncio.TaskGroup() as task_group:
                for task in tasks:
                    task_group.create_task(
                        task(
                            semaphore=semaphore,
                            s3_client=s3_client,
                        )
                    )

    def _get_provisioning_tasks(self, *, input_civs, input_prefixes):
        provisioning_tasks = []
        invocation_inputs = []

        for civ in self._with_inputs_json(input_civs=input_civs):
            for civ_provisioning_task in self._get_civ_provisioning_tasks(
                civ=civ, input_prefixes=input_prefixes
            ):
                provisioning_tasks.append(civ_provisioning_task.task)
                invocation_inputs.append(
                    {
                        "relative_path": str(
                            os.path.relpath(
                                civ_provisioning_task.key, self._io_prefix
                            )
                        ),
                        "bucket_name": settings.COMPONENTS_INPUT_BUCKET_NAME,
                        "bucket_key": civ_provisioning_task.key,
                        "decompress": civ.decompress,
                    }
                )

        provisioning_tasks.append(
            self._get_create_invocation_json_task(
                invocation_inputs=invocation_inputs
            )
        )

        provisioning_tasks.extend(self._auxiliary_data_provisioning_tasks)

        return provisioning_tasks

    @staticmethod
    def _get_civ_target_relative_path(*, civ):
        """
        Where should the file be located?
        """
        relative_path = Path(civ.interface.relative_path)

        if (
            civ.interface.super_kind == civ.interface.SuperKind.IMAGE
            and civ.interface.is_panimg_kind
        ):
            # As these are potentially mhd/(z)raw files their names are fixed
            # Note that this is the name of the file and not the user provided image name
            relative_path /= Path(civ.image_file.name).name

        return relative_path

    def _get_key_for_target_relative_path(
        self, *, civ, input_prefixes, target_relative_path
    ):
        if str(civ.pk) in input_prefixes:
            key = safe_join(
                self._io_prefix,
                input_prefixes[str(civ.pk)],
                target_relative_path,
            )
        else:
            key = safe_join(self._io_prefix, target_relative_path)

        return key

    def _get_civ_provisioning_tasks(self, *, civ, input_prefixes):
        relative_path = self._get_civ_target_relative_path(civ=civ)
        key = self._get_key_for_target_relative_path(
            civ=civ,
            input_prefixes=input_prefixes,
            target_relative_path=relative_path,
        )

        if civ.interface.super_kind == civ.interface.SuperKind.IMAGE:
            if civ.interface.is_dicom_image_kind:
                image_set_id = civ.image.dicom_image_set.image_set_id

                for (
                    image_frame
                ) in civ.image.dicom_image_set.image_frame_metadata:
                    study_instance_uid = image_frame["study_instance_uid"]
                    series_instance_uid = image_frame["series_instance_uid"]
                    sop_instance_uid = image_frame["sop_instance_uid"]
                    stored_transfer_syntax_uid = image_frame[
                        "stored_transfer_syntax_uid"
                    ]

                    key = self._get_key_for_target_relative_path(
                        civ=civ,
                        input_prefixes=input_prefixes,
                        target_relative_path=(
                            relative_path / f"{sop_instance_uid}.dcm"
                        ),
                    )

                    yield CIVProvisioningTask(
                        task=self._get_copy_sop_instance_task(
                            image_set_id=image_set_id,
                            study_instance_uid=study_instance_uid,
                            series_instance_uid=series_instance_uid,
                            sop_instance_uid=sop_instance_uid,
                            stored_transfer_syntax_uid=stored_transfer_syntax_uid,
                            target_key=key,
                        ),
                        key=key,
                    )
            else:
                yield CIVProvisioningTask(
                    task=self._get_copy_input_object_task(
                        src=civ.image_file, target_key=key
                    ),
                    key=key,
                )
        elif civ.interface.super_kind == civ.interface.SuperKind.FILE:
            yield CIVProvisioningTask(
                task=self._get_copy_input_object_task(
                    src=civ.file, target_key=key
                ),
                key=key,
            )
        elif civ.interface.super_kind == civ.interface.SuperKind.VALUE:
            yield CIVProvisioningTask(
                task=self._get_upload_input_content_task(
                    content=json.dumps(civ.value).encode("utf-8"),
                    key=key,
                ),
                key=key,
            )
        else:
            raise NotImplementedError(
                f"Unknown interface super kind: {civ.interface.super_kind}"
            )

    def _get_create_invocation_json_task(self, *, invocation_inputs):
        return self._get_upload_input_content_task(
            content=json.dumps(
                [
                    {
                        "pk": self._job_id,
                        "inputs": invocation_inputs,
                        "output_bucket_name": settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        "output_prefix": self._io_prefix,
                    }
                ]
            ).encode("utf-8"),
            key=self._invocation_key,
        )

    @property
    def _auxiliary_data_provisioning_tasks(self):
        tasks = []

        if self._algorithm_model:
            tasks.append(
                self._get_copy_input_object_task(
                    src=self._algorithm_model,
                    target_key=self._algorithm_model_key,
                )
            )

        if self._ground_truth:
            tasks.append(
                self._get_copy_input_object_task(
                    src=self._ground_truth, target_key=self._ground_truth_key
                )
            )

        return tasks

    def _with_inputs_json(self, *, input_civs):
        """
        An iterator over all inputs along with the special inputs.json,
        which serialises the metadata for all the other inputs such as
        the socket description.
        """
        yield from input_civs

        serializer = ComponentInterfaceValueSerializer(input_civs, many=True)
        yield ComponentInterfaceValue(
            value=serializer.data,
            interface=ComponentInterface(
                relative_path="inputs.json", kind=InterfaceKindChoices.ANY
            ),
        )

    @staticmethod
    def _get_copy_sop_instance_task(
        *,
        image_set_id,
        study_instance_uid,
        series_instance_uid,
        sop_instance_uid,
        stored_transfer_syntax_uid,
        target_key,
    ):
        raise NotImplementedError

    @staticmethod
    def _get_copy_input_object_task(*, src, target_key):
        return functools.partial(
            s3_copy,
            source_bucket=src.storage.bucket.name,
            source_key=src.name,
            target_bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            target_key=target_key,
        )

    @staticmethod
    def _get_upload_input_content_task(*, content, key):
        return functools.partial(
            s3_upload_content,
            content=content,
            bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            key=key,
        )

    def _get_task_return_code(self):
        with io.BytesIO() as fileobj:
            try:
                self._s3_client.download_fileobj(
                    Fileobj=fileobj,
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=self._result_key,
                )
            except botocore.exceptions.ClientError as error:
                if error.response["Error"]["Code"] == "404":
                    raise UncleanExit(
                        "The invocation request did not return a result"
                    ) from error
                else:
                    raise

            fileobj.seek(0)

            try:
                result = json.loads(
                    fileobj.read().decode("utf-8"),
                )
            except JSONDecodeError:
                raise ComponentException(
                    "The invocation request did not return valid json"
                )

            logger.info(f"{result=}")

            if result["pk"] != self._job_id:
                raise RuntimeError("Wrong result key for this job")

            try:
                return int(result["return_code"])
            except (KeyError, ValueError):
                raise ComponentException(
                    "The invocation response object is not valid"
                )

    def _handle_completed_job(self):
        users_process_exit_code = self._get_task_return_code()

        if users_process_exit_code == 0:
            # Job's a good un
            return
        elif users_process_exit_code == 137:
            raise ComponentException(
                "The container was killed as it exceeded its memory limit"
            )
        else:
            raise ComponentException(user_error(self.stderr))

    def _create_images_result(self, *, interface):
        prefix = safe_join(self._io_prefix, interface.relative_path)

        response = self._s3_client.list_objects_v2(
            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            Prefix=(prefix.lstrip("/") if settings.USING_MINIO else prefix),
        )

        if response.get("IsTruncated", False):
            raise ComponentException(
                f"Too many files produced in {interface.relative_path!r}"
            )

        output_files = response.get("Contents", [])
        if not output_files:
            raise ComponentException(
                f"Output directory {interface.relative_path!r} is empty"
            )

        with TemporaryDirectory() as tmpdir:
            self._download_output_files(
                output_files=output_files, tmpdir=tmpdir, prefix=prefix
            )

            try:
                importer_result = import_images(
                    input_directory=tmpdir,
                    builders=[image_builder_mhd, image_builder_tiff],
                )
            except RuntimeError as error:
                if "std::bad_alloc" in str(error):
                    raise ComponentException(
                        "The output image was too large to process, "
                        "please try again with smaller images"
                    ) from error
                else:
                    raise

        if len(importer_result.new_images) == 0:
            raise ComponentException(
                message=f"No output images could be imported from {interface.relative_path!r}",
                message_details=importer_result.file_errors,
            )
        elif len(importer_result.new_images) > 1:
            raise ComponentException(
                f"Only 1 image should be produced in {interface.relative_path!r}, "
                f"we found {len(importer_result.new_images)}"
            )

        try:
            civ = interface.create_instance(
                image=next(iter(importer_result.new_images))
            )
        except ValidationError as e:
            raise ComponentException(
                f"The image produced in {interface.relative_path!r} is not valid. {format_validation_error_message(error=e)}"
            )

        return civ

    def _download_output_files(self, *, output_files, tmpdir, prefix):
        for file in output_files:
            try:
                root_key = safe_join("/", file["Key"])
                dest = safe_join(tmpdir, Path(root_key).relative_to(prefix))
            except (SuspiciousFileOperation, ValueError):
                logger.warning(f"Skipping {file=}")
                continue

            logger.info(
                f"Downloading {file['Key']} to {dest} from "
                f"{settings.COMPONENTS_OUTPUT_BUCKET_NAME}"
            )

            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            self._s3_client.download_file(
                Filename=dest,
                Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                Key=file["Key"],
            )

    def _create_json_result(self, *, interface):
        key = safe_join(self._io_prefix, interface.relative_path)

        try:
            with io.BytesIO() as fileobj:
                self._s3_client.download_fileobj(
                    Fileobj=fileobj,
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=key,
                )
                fileobj.seek(0)
                result = json.loads(
                    fileobj.read().decode("utf-8"),
                    parse_constant=lambda x: None,  # Removes -inf, inf and NaN
                )
            civ = interface.create_instance(value=result)
        except botocore.exceptions.ClientError:
            raise ComponentException(
                f"Output file {interface.relative_path!r} was not produced"
            )
        except MemoryError:
            raise ComponentException(
                f"The output file {interface.relative_path!r} is too large"
            )
        except JSONDecodeError:
            raise ComponentException(
                f"The output file {interface.relative_path!r} is not valid json"
            )
        except ValidationError as e:
            raise ComponentException(
                f"The output file {interface.relative_path!r} is not valid. {format_validation_error_message(error=e)}"
            )

        return civ

    def _create_file_result(self, *, interface):
        key = safe_join(self._io_prefix, interface.relative_path)

        try:
            with SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE) as fileobj:
                self._s3_client.download_fileobj(
                    Fileobj=fileobj,
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=key,
                )
                fileobj.seek(0)
                civ = interface.create_instance(fileobj=fileobj)
        except botocore.exceptions.ClientError:
            raise ComponentException(
                f"Output file {interface.relative_path!r} was not produced"
            )
        except ValidationError as e:
            raise ComponentException(
                f"The output file {interface.relative_path!r} is not valid. {format_validation_error_message(error=e)}"
            )

        return civ

    def _delete_objects(self, *, bucket, prefix):
        """Deletes all objects with a given prefix"""

        list_and_delete_objects_from_prefix(
            s3_client=self._s3_client,
            bucket=bucket,
            prefix=prefix,
        )
