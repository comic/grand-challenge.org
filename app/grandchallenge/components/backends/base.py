import asyncio
import binascii
import functools
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
from abc import ABC, abstractmethod
from datetime import timedelta
from json import JSONDecodeError
from math import ceil
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import NamedTuple
from uuid import UUID

import aioboto3
import boto3
import botocore
import httpx
import pydantic
from asgiref.sync import async_to_sync
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.db import transaction
from django.utils._os import safe_join
from django.utils.functional import cached_property
from panimg.image_builders import image_builder_mhd, image_builder_tiff
from pydantic import BaseModel, ConfigDict
from pydantic_core import to_json

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

MAX_SPOOL_SIZE = settings.GIGABYTE

# For multipart uploads the minimum chunk size is 5 MB
# There is a maximum of 10_000 chunks
# Using a chunk size of 5 MB results in a maximum file size of 50 GB
# The maximum memory used will be ASYNC_CONCURRENCY * S3_CHUNK_SIZE
S3_CHUNK_SIZE = 5 * settings.MEGABYTE

ASYNC_CONCURRENCY = 50
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


def serialize_aws_request(request):
    """
    The kwargs that will be passed to httpx.stream or httpx.request
    to generate a response from an AWSRequest instance.

    External clients use this so the kwargs should not be changed.
    """
    return {
        "url": request.url,
        "method": request.method,
        "data": request.data,
        "headers": dict(request.headers.items()),
    }


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
    httpx_client,  # Unused, but must be present to match signature
):
    async with semaphore:
        await s3_client.copy(
            CopySource={"Bucket": source_bucket, "Key": source_key},
            Bucket=target_bucket,
            Key=target_key,
        )


async def s3_upload_content(
    *,
    content,
    bucket,
    key,
    semaphore,
    s3_client,
    httpx_client,  # Unused, but must be present to match signature
):
    async with semaphore:
        with io.BytesIO() as f:
            f.write(content)
            f.seek(0)

            await s3_client.upload_fileobj(
                Fileobj=f,
                Bucket=bucket,
                Key=key,
            )


async def s3_sign_request_then_stream(*, request, signer, **kwargs):
    """
    Signed requests have a TTL of 5 minutes, so sign just before making the request
    """
    signer.add_auth(request)
    await s3_stream_response(
        request_kwargs=serialize_aws_request(request), **kwargs
    )


async def s3_stream_response(
    *,
    request_kwargs,
    bucket,
    key,
    semaphore,
    s3_client,
    httpx_client,
):
    async with semaphore:
        async with httpx_client.stream(**request_kwargs) as resp:
            resp.raise_for_status()

            multipart_upload = await s3_client.create_multipart_upload(
                Bucket=bucket, Key=key
            )

            upload_id = multipart_upload["UploadId"]
            parts = []
            part_number = 1

            try:
                async for chunk in resp.aiter_bytes(chunk_size=S3_CHUNK_SIZE):
                    if not chunk:
                        continue

                    part_response = await s3_client.upload_part(
                        Bucket=bucket,
                        Key=key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=chunk,
                    )

                    parts.append(
                        {
                            "ETag": part_response["ETag"],
                            "PartNumber": part_number,
                        }
                    )
                    part_number += 1

                await s3_client.complete_multipart_upload(
                    Bucket=bucket,
                    Key=key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )

            except Exception:
                await s3_client.abort_multipart_upload(
                    Bucket=bucket, Key=key, UploadId=upload_id
                )
                raise


class InferenceIO(BaseModel):
    model_config = ConfigDict(frozen=True)

    relative_path: str
    bucket_name: str
    bucket_key: str
    decompress: bool


class InferenceTask(BaseModel):
    model_config = ConfigDict(frozen=True)

    pk: str
    inputs: list[InferenceIO]
    output_bucket_name: str
    output_prefix: str
    timeout: timedelta


class InferenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pk: str
    return_code: int
    exec_duration: timedelta | None
    invoke_duration: timedelta | None
    outputs: list[InferenceIO]
    sagemaker_shim_version: str


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
        signing_key: bytes,
        algorithm_model=None,
        ground_truth=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._job_id = job_id
        self._exec_image_repo_tag = exec_image_repo_tag
        self._memory_limit = memory_limit
        self._time_limit = timedelta(seconds=time_limit)
        self._requires_gpu_type = requires_gpu_type
        self._use_warm_pool = (
            use_warm_pool and settings.COMPONENTS_USE_WARM_POOL
        )
        self._signing_key = signing_key
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
    def utilization_duration(self): ...

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
            "GRAND_CHALLENGE_COMPONENT_MAX_MEMORY_MB": str(
                self._max_memory_mb
            ),
            "GRAND_CHALLENGE_COMPONENT_SIGNING_KEY_HEX": binascii.hexlify(
                self._signing_key
            ).decode("ascii"),
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
        utilization_duration = self.utilization_duration
        if utilization_duration is None:
            return None
        else:
            return duration_to_millicents(
                duration=utilization_duration,
                usd_cents_per_hour=self.usd_cents_per_hour,
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
    def _inference_result_key(self):
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
        semaphore = asyncio.Semaphore(ASYNC_CONCURRENCY)
        session = aioboto3.Session()
        timeout = httpx.Timeout(60.0)

        async with session.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            config=ASYNC_BOTO_CONFIG,
        ) as s3_client:
            async with httpx.AsyncClient(timeout=timeout) as httpx_client:
                async with asyncio.TaskGroup() as task_group:
                    for task in tasks:
                        task_group.create_task(
                            task(
                                semaphore=semaphore,
                                s3_client=s3_client,
                                httpx_client=httpx_client,
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
                    InferenceIO(
                        relative_path=str(
                            os.path.relpath(
                                civ_provisioning_task.key, self._io_prefix
                            )
                        ),
                        bucket_name=settings.COMPONENTS_INPUT_BUCKET_NAME,
                        bucket_key=civ_provisioning_task.key,
                        decompress=civ.decompress,
                    )
                )

        provisioning_tasks.append(
            self._get_create_invocation_json_task(
                invocation_inputs=invocation_inputs
            ).task
        )

        provisioning_tasks.extend(
            t.task for t in self._auxiliary_data_provisioning_tasks
        )

        return provisioning_tasks

    def _get_key_for_target_relative_path(
        self,
        *,
        civ,
        input_prefixes,
        filename=None,
    ):
        relative_path = civ.interface.relative_path

        if str(civ.pk) in input_prefixes:
            key = safe_join(
                self._io_prefix, input_prefixes[str(civ.pk)], relative_path
            )
        else:
            key = safe_join(self._io_prefix, relative_path)

        if civ.interface.super_kind == civ.interface.SuperKind.IMAGE:
            if filename:
                key = safe_join(key, filename)
            else:
                raise ValueError("filename must be set for images")
        elif filename:
            raise ValueError("filename must only be set for images")

        return key

    def _get_civ_provisioning_tasks(self, *, civ, input_prefixes):
        if civ.interface.super_kind == civ.interface.SuperKind.IMAGE:
            if civ.interface.is_dicom_image_kind:
                session = boto3.Session(
                    region_name=settings.AWS_DEFAULT_REGION,
                )
                medical_imaging_auth = SigV4Auth(
                    credentials=session.get_credentials(),
                    service_name="medical-imaging",
                    region_name=settings.AWS_DEFAULT_REGION,
                )

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
                        filename=f"{sop_instance_uid}.dcm",
                    )

                    yield self._get_copy_sop_instance_task(
                        medical_imaging_auth=medical_imaging_auth,
                        image_set_id=image_set_id,
                        study_instance_uid=study_instance_uid,
                        series_instance_uid=series_instance_uid,
                        sop_instance_uid=sop_instance_uid,
                        stored_transfer_syntax_uid=stored_transfer_syntax_uid,
                        target_key=key,
                    )
            elif civ.interface.is_panimg_kind:
                image_file = civ.image_file

                # Set the name of the file, note that this is not set by the user.
                # The filenames are sensitive as they are relative for some panimg files.
                key = self._get_key_for_target_relative_path(
                    civ=civ,
                    input_prefixes=input_prefixes,
                    filename=Path(image_file.name).name,
                )

                yield self._get_copy_input_object_task(
                    src=image_file, target_key=key
                )
        elif civ.interface.super_kind == civ.interface.SuperKind.FILE:
            key = self._get_key_for_target_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )

            yield self._get_copy_input_object_task(
                src=civ.file, target_key=key
            )
        elif civ.interface.super_kind == civ.interface.SuperKind.VALUE:
            key = self._get_key_for_target_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )

            yield self._get_upload_input_content_task(
                content=json.dumps(civ.value).encode("utf-8"), key=key
            )
        else:
            raise NotImplementedError(
                f"Unknown interface super kind: {civ.interface.super_kind}"
            )

    def _get_create_invocation_json_task(self, *, invocation_inputs):
        return self._get_upload_input_content_task(
            content=to_json(
                [
                    InferenceTask(
                        pk=self._job_id,
                        inputs=invocation_inputs,
                        output_bucket_name=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        output_prefix=self._io_prefix,
                        timeout=self._time_limit,
                    )
                ]
            ),
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
        medical_imaging_auth,
        image_set_id,
        study_instance_uid,
        series_instance_uid,
        sop_instance_uid,
        stored_transfer_syntax_uid,
        target_key,
    ):
        # See https://docs.aws.amazon.com/healthimaging/latest/devguide/dicomweb-retrieve-instance.html
        dicom_file_url = (
            f"https://dicom-medical-imaging.{settings.AWS_DEFAULT_REGION}.amazonaws.com"
            f"/datastore/{settings.AWS_HEALTH_IMAGING_DATASTORE_ID}"
            f"/studies/{study_instance_uid}"
            f"/series/{series_instance_uid}"
            f"/instances/{sop_instance_uid}"
            f"?imageSetId={image_set_id}"
        )

        request = AWSRequest(
            method="GET",
            url=dicom_file_url,
            headers={
                "Accept": f"application/dicom; transfer-syntax={stored_transfer_syntax_uid}"
            },
        )

        return CIVProvisioningTask(
            task=functools.partial(
                s3_sign_request_then_stream,
                request=request,
                signer=medical_imaging_auth,
                bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                key=target_key,
            ),
            key=target_key,
        )

    @staticmethod
    def _get_copy_input_object_task(*, src, target_key):
        return CIVProvisioningTask(
            task=functools.partial(
                s3_copy,
                source_bucket=src.storage.bucket.name,
                source_key=src.name,
                target_bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                target_key=target_key,
            ),
            key=target_key,
        )

    @staticmethod
    def _get_upload_input_content_task(*, content, key):
        return CIVProvisioningTask(
            task=functools.partial(
                s3_upload_content,
                content=content,
                bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                key=key,
            ),
            key=key,
        )

    def _get_inference_result(self):
        try:
            response = self._s3_client.get_object(
                Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                Key=self._inference_result_key,
            )
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] == "404":
                raise UncleanExit(
                    "The invocation request did not return a result"
                ) from error
            else:
                raise

        body = response["Body"].read()

        signature_hmac_sha256 = response["Metadata"]["signature_hmac_sha256"]
        body_signature_hmac_sha256 = hmac.new(
            key=self._signing_key, msg=body, digestmod=hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(
            body_signature_hmac_sha256, signature_hmac_sha256
        ):
            logger.error(
                "The invocation response object has been tampered with"
            )
            raise ComponentException(
                "The invocation response object has been tampered with"
            )

        try:
            inference_result = InferenceResult.model_validate_json(
                json_data=body
            )
        except pydantic.ValidationError as error:
            logger.error(error, exc_info=True)
            raise ComponentException(
                "The invocation request did not return valid json"
            )

        logger.info(f"{inference_result=}")

        if inference_result.pk != self._job_id:
            raise RuntimeError("Wrong result key for this job")

        return inference_result

    def _handle_completed_job(self):
        inference_result = self._get_inference_result()

        users_process_exit_code = inference_result.return_code

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
