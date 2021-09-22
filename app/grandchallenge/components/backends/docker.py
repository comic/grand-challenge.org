import json
import logging
import os
import sys
import tarfile
from contextlib import contextmanager
from json import JSONDecodeError
from pathlib import Path
from random import randint
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from time import sleep

import docker
from dateutil.parser import isoparse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.utils._os import safe_join
from docker.api.container import ContainerApiMixin
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from docker.tls import TLSConfig
from docker.types import LogConfig
from panimg.image_builders import image_builder_mhd, image_builder_tiff
from requests import HTTPError

from grandchallenge.cases.tasks import import_images
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import LOGLINES, user_error

logger = logging.getLogger(__name__)

MAX_SPOOL_SIZE = 1_000_000_000  # 1GB


class DockerConnection:
    """
    Provides a client with a connection to a docker host, provisioned for
    running the container exec_image.
    """

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
        super().__init__()
        self._job_id = job_id
        self._exec_image_sha256 = exec_image_sha256
        self._exec_image_repo_tag = exec_image_repo_tag
        self._exec_image_file = exec_image_file
        self._memory_limit = memory_limit
        self._requires_gpu = requires_gpu

        self.__client = None

    @property
    def _client(self):
        if self.__client is None:
            client_kwargs = {"base_url": settings.COMPONENTS_DOCKER_BASE_URL}

            if settings.COMPONENTS_DOCKER_TLSVERIFY:
                tlsconfig = TLSConfig(
                    verify=True,
                    client_cert=(
                        settings.COMPONENTS_DOCKER_TLSCERT,
                        settings.COMPONENTS_DOCKER_TLSKEY,
                    ),
                    ca_cert=settings.COMPONENTS_DOCKER_TLSCACERT,
                )
                client_kwargs.update({"tls": tlsconfig})

            self.__client = docker.DockerClient(**client_kwargs)

        return self.__client

    @property
    def _labels(self):
        return {"job": f"{self._job_id}", "traefik.enable": "false"}

    @property
    def _run_kwargs(self):
        return {
            "init": True,
            "network_disabled": True,
            "mem_limit": f"{self._memory_limit}g",
            # Set to the same as mem_limit to avoid using swap
            "memswap_limit": f"{self._memory_limit}g",
            "cpu_period": settings.COMPONENTS_CPU_PERIOD,
            "cpu_quota": settings.COMPONENTS_CPU_QUOTA,
            "cpu_shares": settings.COMPONENTS_CPU_SHARES,
            "cpuset_cpus": self._cpuset_cpus,
            "runtime": settings.COMPONENTS_DOCKER_RUNTIME,
            "cap_drop": ["all"],
            "security_opt": ["no-new-privileges"],
            "pids_limit": settings.COMPONENTS_PIDS_LIMIT,
            "log_config": LogConfig(
                type=LogConfig.types.JSON, config={"max-size": "1g"}
            ),
        }

    @property
    def _cpuset_cpus(self):
        """
        The cpuset_cpus as a string.

        Returns
        -------
            The setting COMPONENTS_CPUSET_CPUS if this is set to a
            none-empty string. Otherwise, works out the available cpu
            from the os.
        """
        if settings.COMPONENTS_CPUSET_CPUS:
            return settings.COMPONENTS_CPUSET_CPUS
        else:
            # Get the cpu count, note that this is setting up the container
            # so that it can use all of the CPUs on the system. To limit
            # the containers execution set COMPONENTS_CPUSET_CPUS
            # externally.
            cpus = os.cpu_count()
            if cpus in [None, 1]:
                return "0"
            else:
                return f"0-{cpus - 1}"

    @staticmethod
    def __retry_docker_obj_prune(*, obj, filters: dict):
        # Retry and exponential backoff of the prune command as only 1 prune
        # operation can occur at a time on a docker host
        num_retries = 0
        e = Exception
        while num_retries < 10:
            try:
                obj.prune(filters=filters)
                break
            except (APIError, HTTPError) as _e:
                num_retries += 1
                e = _e
                sleep((2 ** num_retries) + (randint(0, 1000) / 1000))
        else:
            raise e

    def stop_and_cleanup(self, timeout: int = 10):
        """Stops and prunes all containers associated with this job."""
        flt = {"label": f"job={self._job_id}"}

        for c in self._client.containers.list(filters=flt):
            c.stop(timeout=timeout)

        self.__retry_docker_obj_prune(obj=self._client.containers, filters=flt)
        self.__retry_docker_obj_prune(obj=self._client.volumes, filters=flt)

    def _pull_images(self):
        try:
            self._client.images.get(name=self._exec_image_sha256)
        except ImageNotFound:
            # This can take a long time so increase the default timeout #1330
            old_timeout = self._client.api.timeout
            self._client.api.timeout = 600  # 10 minutes

            with SpooledTemporaryFile(
                max_size=MAX_SPOOL_SIZE
            ) as fdst, self._exec_image_file.open("rb") as fsrc:
                copyfileobj(fsrc=fsrc, fdst=fdst)
                fdst.seek(0)
                self._client.images.load(fdst)

            self._client.api.timeout = old_timeout


class DockerExecutor(DockerConnection):
    IS_EVENT_DRIVEN = False

    @staticmethod
    def get_job_params(*, event):
        raise NotImplementedError

    def provision(self, *, input_civs, input_prefixes):
        self._pull_images()
        self._create_io_volumes()
        self._provision_input_volume(
            input_civs=input_civs, input_prefixes=input_prefixes
        )
        self._chmod_volumes()

    def execute(self):
        self._pull_images()
        self._execute_container()

    def handle_event(self):
        pass

    def get_outputs(self, *, output_interfaces):
        self._pull_images()
        return self._get_outputs(output_interfaces=output_interfaces)

    def deprovision(self):
        self.stop_and_cleanup()

    @property
    def stdout(self):
        try:
            container = self._execution_container
            return (
                container.logs(
                    stdout=True, stderr=False, timestamps=True, tail=LOGLINES
                )
                .replace(b"\x00", b"")
                .decode("utf-8")
            )
        except DockerException as e:
            logger.warning(f"Could not fetch stdout: {e}")
            return ""

    @property
    def stderr(self):
        try:
            container = self._execution_container
            return (
                container.logs(
                    stdout=False, stderr=True, timestamps=True, tail=LOGLINES
                )
                .replace(b"\x00", b"")
                .decode("utf-8")
            )
        except DockerException as e:
            logger.warning(f"Could not fetch stderr: {e}")
            return ""

    @property
    def duration(self):
        try:
            container = self._execution_container
            if container.status == "exited":
                state = self._client.api.inspect_container(
                    container=container.id
                )
                started_at = state["State"]["StartedAt"]
                finished_at = state["State"]["FinishedAt"]
                return isoparse(finished_at) - isoparse(started_at)
            else:
                return None
        except DockerException as e:
            logger.warning(f"Could not inspect container: {e}")
            return None

    @property
    def _input_volume_name(self):
        return f"{self._job_id}-input"

    @property
    def _output_volume_name(self):
        return f"{self._job_id}-output"

    @property
    def _execution_container_name(self):
        return f"{self._job_id}-executor"

    @property
    def _execution_container(self):
        return self._client.containers.get(
            container_id=self._execution_container_name
        )

    def _pull_images(self):
        try:
            self._client.images.get(name=settings.COMPONENTS_IO_IMAGE)
        except ImageNotFound:
            self._client.images.pull(repository=settings.COMPONENTS_IO_IMAGE)

        super()._pull_images()

    def _create_io_volumes(self):
        for volume in [self._input_volume_name, self._output_volume_name]:
            self._client.volumes.create(name=volume, labels=self._labels)

    def _provision_input_volume(self, *, input_civs, input_prefixes):
        with stop(
            self._client.containers.run(
                image=settings.COMPONENTS_IO_IMAGE,
                volumes={
                    self._input_volume_name: {"bind": "/input/", "mode": "rw"}
                },
                name=f"{self._job_id}-writer",
                remove=True,
                detach=True,
                tty=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        ) as writer:
            self._copy_input_files(
                writer=writer,
                input_civs=input_civs,
                input_prefixes=input_prefixes,
            )

    def _copy_input_files(self, *, writer, input_civs, input_prefixes):
        for civ in input_civs:
            prefix = "/input/"

            if str(civ.pk) in input_prefixes:
                prefix = safe_join(prefix, input_prefixes[str(civ.pk)])

            if civ.decompress:
                dest = Path(
                    safe_join("/tmp/", prefix.lstrip("/"), "submission-src")
                )
            else:
                dest = Path(safe_join(prefix, civ.relative_path))

            writer.exec_run(f"mkdir -p {dest.parent}")
            put_file(
                container=writer, src=civ.input_file, dest=dest,
            )

            if civ.decompress:
                # Decompression is legacy for submission evaluations where
                # we offered to unzip prediction files for challenge admins
                if prefix[0] != "/" or prefix[-1] != "/":
                    raise RuntimeError(f"Prefix {prefix} is not a full path")

                writer.exec_run(f"unzip {dest} -d {prefix} -x '__MACOSX/*'")

                # Remove a duplicated directory
                input_files = (
                    writer.exec_run(f"ls -1 {prefix}")
                    .output.decode()
                    .splitlines()
                )

                if (
                    len(input_files) == 1
                    and not writer.exec_run(
                        f"ls -d {prefix}{input_files[0]}/"
                    ).exit_code
                ):
                    writer.exec_run(
                        f'/bin/sh -c "mv {prefix}{input_files[0]}/* {prefix} '
                        f'&& rm -r {prefix}{input_files[0]}/"'
                    )

    def _chmod_volumes(self):
        """Ensure that the i/o directories are writable."""
        self._client.containers.run(
            image=settings.COMPONENTS_IO_IMAGE,
            volumes={
                self._input_volume_name: {"bind": "/input/", "mode": "rw"},
                self._output_volume_name: {"bind": "/output/", "mode": "rw"},
            },
            name=f"{self._job_id}-chmod-volumes",
            command="chmod -R 0777 /input/ /output/",
            remove=True,
            labels=self._labels,
            **self._run_kwargs,
        )

    def _execute_container(self) -> None:
        with stop(
            self._client.containers.run(
                image=self._exec_image_sha256,
                volumes={
                    self._input_volume_name: {"bind": "/input/", "mode": "ro"},
                    self._output_volume_name: {
                        "bind": "/output/",
                        "mode": "rw",
                    },
                },
                name=self._execution_container_name,
                detach=True,
                labels=self._labels,
                environment={
                    "NVIDIA_VISIBLE_DEVICES": settings.COMPONENTS_NVIDIA_VISIBLE_DEVICES
                },
                **self._run_kwargs,
            )
        ) as c:
            container_state = c.wait()

        exit_code = int(container_state["StatusCode"])
        if exit_code == 137:
            raise ComponentException(
                "The container was killed as it exceeded the memory limit "
                f"of {self._run_kwargs['mem_limit']}."
            )
        elif exit_code != 0:
            raise ComponentException(user_error(self.stderr))

    def _get_outputs(self, *, output_interfaces):
        """Create ComponentInterfaceValues from the output interfaces"""
        outputs = []

        with stop(
            self._client.containers.run(
                image=settings.COMPONENTS_IO_IMAGE,
                volumes={
                    self._output_volume_name: {
                        "bind": "/output/",
                        "mode": "ro",
                    }
                },
                name=f"{self._job_id}-reader",
                remove=True,
                detach=True,
                tty=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        ) as reader:
            with transaction.atomic():
                # Atomic block required as create_instance needs to
                # create interfaces in order to store the files
                for interface in output_interfaces:
                    if interface.is_image_kind:
                        res = self._create_images_result(
                            interface=interface, reader=reader
                        )
                    else:
                        res = self._create_file_result(
                            interface=interface, reader=reader
                        )

                    outputs.append(res)

        return outputs

    def _create_images_result(self, *, interface, reader):
        base_dir = Path(safe_join("/output/", interface.relative_path))
        found_files = reader.exec_run(f"find {base_dir} -type f")

        if found_files.exit_code != 0:
            raise ComponentException(f"Error listing {base_dir}")

        output_files = [
            base_dir / Path(f)
            for f in found_files.output.decode().splitlines()
        ]

        if not output_files:
            raise ComponentException(f"{base_dir} is empty")

        with TemporaryDirectory() as tmpdir:
            for file in output_files:
                temp_file = Path(safe_join(tmpdir, file.relative_to(base_dir)))
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                get_file(container=reader, src=file, dest=temp_file)

            importer_result = import_images(
                input_directory=tmpdir,
                builders=[image_builder_mhd, image_builder_tiff],
            )

        if len(importer_result.new_images) == 0:
            raise ComponentException(f"No images imported from {base_dir}")
        elif len(importer_result.new_images) > 1:
            raise ComponentException(
                f"Only 1 image should be produced in {base_dir}, "
                f"we found {len(importer_result.new_images)}"
            )

        try:
            civ = interface.create_instance(
                image=next(iter(importer_result.new_images))
            )
        except ValidationError:
            raise ComponentException(
                f"The image produced in {base_dir} is not valid"
            )

        return civ

    def _create_file_result(self, *, interface, reader):
        output_file = Path(safe_join("/output/", interface.relative_path))

        try:
            with TemporaryDirectory() as tmpdir:
                temp_file = Path(safe_join(tmpdir, "output.json"))
                get_file(container=reader, src=output_file, dest=temp_file)

                with open(temp_file, "rb") as file:
                    result = json.loads(
                        file.read().decode("utf-8"),
                        parse_constant=lambda x: None,  # Removes -inf, inf and NaN
                    )
        except NotFound:
            raise ComponentException(f"File {output_file} was not produced")
        except JSONDecodeError:
            raise ComponentException(
                f"The file produced at {output_file} is not valid json"
            )

        try:
            civ = interface.create_instance(value=result)
        except ValidationError:
            raise ComponentException(
                f"The file produced at {output_file} is not valid"
            )

        return civ


class Service(DockerConnection):
    @property
    def _run_kwargs(self):
        kwargs = super()._run_kwargs
        kwargs.update(
            {
                # Allow networking for service containers
                "network_disabled": False,
                "network": settings.WORKSTATIONS_NETWORK_NAME,
            }
        )
        return kwargs

    @property
    def extra_hosts(self):
        if settings.DEBUG:
            # The workstation needs to communicate with the django api. In
            # production this happens automatically via the external DNS, but
            # when running in debug mode we need to pass through the developers
            # host via the workstations network gateway

            network = self._client.networks.list(
                names=[settings.WORKSTATIONS_NETWORK_NAME]
            )[0]

            return {
                "gc.localhost": network.attrs.get("IPAM")["Config"][0][
                    "Gateway"
                ]
            }
        else:
            return {}

    @property
    def container(self):
        return self._client.containers.get(f"{self._job_id}-service")

    def logs(self) -> str:
        """Get the container logs for this service."""
        try:
            logs = self.container.logs().decode()
        except APIError as e:
            logs = str(e)

        return logs

    def start(
        self,
        http_port: int,
        websocket_port: int,
        hostname: str,
        environment: dict = None,
    ):
        self._pull_images()

        if "." in hostname:
            raise ValueError("Hostname cannot contain a '.'")

        traefik_labels = {
            "traefik.enable": "true",
            f"traefik.http.routers.{hostname}-http.rule": f"Host(`{hostname}`)",
            f"traefik.http.routers.{hostname}-http.service": f"{hostname}-http",
            f"traefik.http.routers.{hostname}-http.entrypoints": "workstation-http",
            f"traefik.http.services.{hostname}-http.loadbalancer.server.port": str(
                http_port
            ),
            f"traefik.http.routers.{hostname}-websocket.rule": f"Host(`{hostname}`)",
            f"traefik.http.routers.{hostname}-websocket.service": f"{hostname}-websocket",
            f"traefik.http.routers.{hostname}-websocket.entrypoints": "workstation-websocket",
            f"traefik.http.services.{hostname}-websocket.loadbalancer.server.port": str(
                websocket_port
            ),
        }

        self._client.containers.run(
            image=self._exec_image_sha256,
            name=f"{self._job_id}-service",
            remove=True,
            detach=True,
            labels={**self._labels, **traefik_labels},
            environment=environment or {},
            extra_hosts=self.extra_hosts,
            **self._run_kwargs,
        )


@contextmanager
def stop(container: ContainerApiMixin):
    """
    Stops a docker container which is running in detached mode

    :param container: An instance of a container
    :return:
    """
    try:
        yield container

    finally:
        container.stop()


def put_file(*, container: ContainerApiMixin, src: File, dest: Path) -> ():
    """
    Puts a file on the host into a container.
    This method will create an in memory tar archive, add the src file to this
    and upload it to the docker container where it will be unarchived at dest.

    :param container: The container to write to
    :param src: The path to the source file on the host
    :param dest: The path to the target file in the container
    :return:
    """
    with SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE) as tar_b:
        tarinfo = tarfile.TarInfo(name=os.path.basename(dest))
        tarinfo.size = getattr(src, "size", sys.getsizeof(src))

        with tarfile.open(fileobj=tar_b, mode="w") as tar, src.open("rb") as f:
            tar.addfile(tarinfo, fileobj=f)

        tar_b.seek(0)
        container.put_archive(os.path.dirname(dest), tar_b)


def get_file(*, container: ContainerApiMixin, src: Path, dest: Path):
    """Gets a file from src in the container and writes it to dest"""
    tarstrm, info = container.get_archive(src)

    with SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE) as ftmp, open(
        dest, "wb"
    ) as outfile:
        for t in tarstrm:
            ftmp.write(t)
        ftmp.seek(0)

        tar = tarfile.open(mode="r", fileobj=ftmp)
        infile = tar.extractfile(src.name)

        buffer = True
        while buffer:
            buffer = infile.read(1024)
            outfile.write(buffer)
