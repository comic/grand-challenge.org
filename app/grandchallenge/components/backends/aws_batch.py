import json
import shutil
from json import JSONDecodeError
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.utils._os import safe_join
from panimg.image_builders import image_builder_mhd, image_builder_tiff

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.exceptions import ComponentException


class AWSBatchExecutor:
    def __init__(
        self,
        *,
        job_id: str,
        exec_image_sha256: str,
        exec_image_repo_tag: str,
        exec_image_file: File,
        memory_limit: int = settings.COMPONENTS_MEMORY_LIMIT,
    ):
        self._job_id = job_id
        self._exec_image_sha256 = exec_image_sha256
        self._exec_image_repo_tag = exec_image_repo_tag
        self._exec_image_file = exec_image_file
        self._memory_limit = min(
            memory_limit, settings.COMPONENTS_MEMORY_LIMIT
        )

    def provision(self, *, input_civs, input_prefixes):
        self._create_io_volumes()
        self._copy_input_files(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def execute(self):
        # TODO - Implement scheduling Task on AWS Batch
        self._copy_to_output()

    def await_completion(self):
        # TODO - Implement waiting on AWS Batch Task
        pass

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

    @property
    def stdout(self):
        # TODO Implement fetching logs from AWS Batch Task
        return ""

    @property
    def stderr(self):
        # TODO Implement fetching logs from AWS Batch Task
        return ""

    @property
    def duration(self):
        # TODO Implement fetching execution duration from AWS Batch Task
        return None

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

    def _copy_to_output(self):
        # TODO This task is just for testing
        res = {}
        files = {x for x in self._input_directory.rglob("*") if x.is_file()}

        for file in files:
            try:
                with open(file) as f:
                    val = json.loads(f.read())
            except Exception:
                val = "file"

            res[str(file.absolute())] = val

            new_file = self._output_directory / file.relative_to(
                self._input_directory
            )
            new_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, new_file)

        for output_filename in ["results", "metrics"]:
            with open(
                self._output_directory / f"{output_filename}.json", "w"
            ) as f:
                f.write(json.dumps(res))

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
            # TODO add option to not recurse subdirectories
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
