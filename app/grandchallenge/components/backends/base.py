import io
import json
import logging
import os
from abc import ABC, abstractmethod
from json import JSONDecodeError
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import NamedTuple
from uuid import UUID

import boto3
import botocore
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils._os import safe_join
from panimg.image_builders import image_builder_mhd, image_builder_tiff

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.exceptions import ComponentException

logger = logging.getLogger(__name__)

MAX_SPOOL_SIZE = 1_000_000_000  # 1GB


class JobParams(NamedTuple):
    app_label: str
    model_name: str
    pk: UUID


class Executor(ABC):
    IS_EVENT_DRIVEN = False

    def __init__(
        self,
        *args,
        job_id: str,
        exec_image_repo_tag: str,
        memory_limit: int,
        time_limit: int,
        requires_gpu: bool,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._job_id = job_id
        self._exec_image_repo_tag = exec_image_repo_tag
        self._memory_limit = memory_limit
        self._time_limit = time_limit
        self._requires_gpu = requires_gpu
        self._stdout = []
        self._stderr = []
        self.__s3_client = None

    def provision(self, *, input_civs, input_prefixes):
        self._provision_inputs(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    @abstractmethod
    def execute(self, *, input_civs, input_prefixes):
        ...

    def handle_event(self, *, event):
        pass

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

    @staticmethod
    @abstractmethod
    def get_job_params(*, event):
        ...

    @classmethod
    def update_filesystem(cls):
        pass

    @property
    def stdout(self):
        return "\n".join(self._stdout)

    @property
    def stderr(self):
        return "\n".join(self._stderr)

    @property
    @abstractmethod
    def duration(self):
        ...

    @property
    @abstractmethod
    def runtime_metrics(self):
        ...

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
    def _s3_client(self):
        if self.__s3_client is None:
            self.__s3_client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            )
        return self.__s3_client

    def _get_key_and_relative_path(self, *, civ, input_prefixes):
        if str(civ.pk) in input_prefixes:
            key = safe_join(
                self._io_prefix, input_prefixes[str(civ.pk)], civ.relative_path
            )
        else:
            key = safe_join(self._io_prefix, civ.relative_path)

        relative_path = str(os.path.relpath(key, self._io_prefix))

        return key, relative_path

    def _get_invocation_json(self, *, input_civs, input_prefixes):
        inputs = []
        for civ in input_civs:
            key, relative_path = self._get_key_and_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )
            inputs.append(
                {
                    "relative_path": relative_path,
                    "bucket_name": settings.COMPONENTS_INPUT_BUCKET_NAME,
                    "bucket_key": key,
                    "decompress": civ.decompress,
                }
            )

        return {
            "pk": self._job_id,
            "inputs": inputs,
            "output_bucket_name": settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            "output_prefix": self._io_prefix,
        }

    def _provision_inputs(self, *, input_civs, input_prefixes):
        for civ in input_civs:
            key, _ = self._get_key_and_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )

            with civ.input_file.open("rb") as f:
                # TODO replace this with server side copy
                self._s3_client.upload_fileobj(
                    Fileobj=f,
                    Bucket=settings.COMPONENTS_INPUT_BUCKET_NAME,
                    Key=key,
                )

    def _create_images_result(self, *, interface):
        prefix = safe_join(self._io_prefix, interface.relative_path)
        response = self._s3_client.list_objects_v2(
            Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
            Prefix=prefix,
        )

        if response.get("IsTruncated", False):
            raise ComponentException(
                f"Too many files produced in '{interface.relative_path}'"
            )

        output_files = response["Contents"]
        if not output_files:
            raise ComponentException(
                f"Output directory '{interface.relative_path}' is empty"
            )

        with TemporaryDirectory() as tmpdir:
            for file in output_files:
                key = safe_join("/", file["Key"])
                dest = safe_join(tmpdir, Path(key).relative_to(prefix))

                logger.info(
                    f"Downloading {key} to {dest} from "
                    f"{settings.COMPONENTS_OUTPUT_BUCKET_NAME}"
                )

                Path(dest).parent.mkdir(parents=True, exist_ok=True)
                self._s3_client.download_file(
                    Filename=dest,
                    Bucket=settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    Key=key,
                )

            importer_result = import_images(
                input_directory=tmpdir,
                builders=[image_builder_mhd, image_builder_tiff],
            )

        if len(importer_result.new_images) == 0:
            raise ComponentException(
                f"No output images could be imported from '{interface.relative_path}'"
            )
        elif len(importer_result.new_images) > 1:
            raise ComponentException(
                f"Only 1 image should be produced in '{interface.relative_path}', "
                f"we found {len(importer_result.new_images)}"
            )

        try:
            civ = interface.create_instance(
                image=next(iter(importer_result.new_images))
            )
        except ValidationError:
            raise ComponentException(
                f"The image produced in '{interface.relative_path}' is not valid"
            )

        return civ

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
                f"Output file '{interface.relative_path}' was not produced"
            )
        except JSONDecodeError:
            raise ComponentException(
                f"The output file '{interface.relative_path}' is not valid json"
            )
        except ValidationError:
            raise ComponentException(
                f"The output file '{interface.relative_path}' is not valid"
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
                f"Output file '{interface.relative_path}' was not produced"
            )
        except ValidationError:
            raise ComponentException(
                f"The output file '{interface.relative_path}' is not valid"
            )

        return civ

    def _delete_objects(self, *, bucket, prefix):
        """Deletes all objects with a given prefix"""
        if not (
            prefix.startswith("/io/") or prefix.startswith("/invocations/")
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
            Prefix=prefix,
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
