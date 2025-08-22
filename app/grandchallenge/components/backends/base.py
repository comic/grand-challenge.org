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

import boto3
import botocore
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


class JobParams(NamedTuple):
    app_label: str
    model_name: str
    pk: UUID
    attempt: int


def duration_to_millicents(*, duration, usd_cents_per_hour):
    return ceil(
        (duration.total_seconds() / 3600)
        * usd_cents_per_hour
        * 1000
        * settings.COMPONENTS_USD_TO_EUR
        * (1 + settings.COMPONENTS_TAX_RATE_PERCENT)
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
        self._provision_inputs(
            input_civs=input_civs, input_prefixes=input_prefixes
        )
        self._provision_auxilliary_data()

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

    def _get_key_and_relative_path(self, *, civ, input_prefixes):
        if str(civ.pk) in input_prefixes:
            key = safe_join(
                self._io_prefix, input_prefixes[str(civ.pk)], civ.relative_path
            )
        else:
            key = safe_join(self._io_prefix, civ.relative_path)

        relative_path = str(os.path.relpath(key, self._io_prefix))

        return key, relative_path

    def _provision_inputs(self, *, input_civs, input_prefixes):
        invocation_inputs = []

        for civ in self._with_inputs_json(input_civs=input_civs):
            key, relative_path = self._get_key_and_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )

            if civ.image:
                self._copy_input_file(src=civ.image_file, dest_key=key)
            elif civ.file:
                self._copy_input_file(src=civ.file, dest_key=key)
            else:
                with io.BytesIO() as f:
                    f.write(json.dumps(civ.value).encode("utf-8"))
                    f.seek(0)
                    self._s3_client.upload_fileobj(
                        Fileobj=f,
                        Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                        Key=key,
                    )

            invocation_inputs.append(
                {
                    "relative_path": relative_path,
                    "bucket_name": settings.COMPONENTS_INPUT_BUCKET_NAME,
                    "bucket_key": key,
                    "decompress": civ.decompress,
                }
            )

        self._create_invocation_json(inputs=invocation_inputs)

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

    def _create_invocation_json(self, *, inputs):
        f = io.BytesIO(
            json.dumps(
                [
                    {
                        "pk": self._job_id,
                        "inputs": inputs,
                        "output_bucket_name": settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                        "output_prefix": self._io_prefix,
                    }
                ]
            ).encode("utf-8")
        )
        self._s3_client.upload_fileobj(
            f, settings.COMPONENTS_INPUT_BUCKET_NAME, self._invocation_key
        )

    def _provision_auxilliary_data(self):
        if self._algorithm_model:
            self._copy_input_file(
                src=self._algorithm_model, dest_key=self._algorithm_model_key
            )
        if self._ground_truth:
            self._copy_input_file(
                src=self._ground_truth, dest_key=self._ground_truth_key
            )

    def _copy_input_file(self, *, src, dest_key):
        self._s3_client.copy(
            CopySource={"Bucket": src.storage.bucket.name, "Key": src.name},
            Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
            Key=dest_key,
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
        if not (
            prefix.startswith("/io/")
            or prefix.startswith("/invocations/")
            or prefix.startswith("/training-outputs/")
            or prefix.startswith("/auxiliary-data/")
        ) or bucket not in {
            settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            settings.COMPONENTS_INPUT_BUCKET_NAME,
        }:
            # Guard against deleting something unexpected
            raise RuntimeError(
                "Deleting from this prefix or bucket is not allowed"
            )

        objects_list = self._s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=(prefix.lstrip("/") if settings.USING_MINIO else prefix),
        )

        if contents := objects_list.get("Contents"):
            response = self._s3_client.delete_objects(
                Bucket=bucket,
                Delete={
                    "Objects": [
                        {"Key": content["Key"]} for content in contents
                    ],
                },
            )
            logger.debug(f"Deleted {response.get('Deleted')} from {bucket}")
            errors = response.get("Errors")
        else:
            logger.debug(f"No objects found in {bucket}/{prefix}")
            errors = None

        if objects_list["IsTruncated"] or errors:
            logger.error("Not all files were deleted")
