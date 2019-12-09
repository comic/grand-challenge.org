import io
import json
import os
import tarfile
from contextlib import contextmanager
from json import JSONDecodeError
from pathlib import Path
from random import randint
from time import sleep
from typing import Tuple

import docker
from django.conf import settings
from django.core.files import File
from docker.api.container import ContainerApiMixin
from docker.errors import APIError, ContainerError, NotFound
from docker.tls import TLSConfig
from docker.types import LogConfig
from requests import HTTPError


class DockerConnection:
    """
    Provides a client with a connection to a docker host, provisioned for
    running the container exec_image.
    """

    def __init__(
        self,
        *,
        job_id: str,
        job_model: str,
        exec_image: File,
        exec_image_sha256: str,
    ):
        super().__init__()
        self._job_id = job_id
        self._job_label = f"{job_model}-{job_id}"
        self._exec_image = exec_image
        self._exec_image_sha256 = exec_image_sha256

        client_kwargs = {"base_url": settings.CONTAINER_EXEC_DOCKER_BASE_URL}

        if settings.CONTAINER_EXEC_DOCKER_TLSVERIFY:
            tlsconfig = TLSConfig(
                verify=True,
                client_cert=(
                    settings.CONTAINER_EXEC_DOCKER_TLSCERT,
                    settings.CONTAINER_EXEC_DOCKER_TLSKEY,
                ),
                ca_cert=settings.CONTAINER_EXEC_DOCKER_TLSCACERT,
            )
            client_kwargs.update({"tls": tlsconfig})

        self._client = docker.DockerClient(**client_kwargs)

        self._labels = {"job": f"{self._job_label}", "traefik.enable": "false"}

        self._run_kwargs = {
            "init": True,
            "network_disabled": True,
            "mem_limit": settings.CONTAINER_EXEC_MEMORY_LIMIT,
            # Set to the same as mem_limit to avoid using swap
            "memswap_limit": settings.CONTAINER_EXEC_MEMORY_LIMIT,
            "cpu_period": settings.CONTAINER_EXEC_CPU_PERIOD,
            "cpu_quota": settings.CONTAINER_EXEC_CPU_QUOTA,
            "cpu_shares": settings.CONTAINER_EXEC_CPU_SHARES,
            "runtime": settings.CONTAINER_EXEC_DOCKER_RUNTIME,
            "cap_drop": ["all"],
            "security_opt": ["no-new-privileges"],
            "pids_limit": settings.CONTAINER_EXEC_PIDS_LIMIT,
            "log_config": LogConfig(
                type=LogConfig.types.JSON, config={"max-size": "1g"}
            ),
        }

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
        """Stops and prunes all artifacts associated with this job."""
        flt = {"label": f"job={self._job_label}"}

        try:
            for c in self._client.containers.list(filters=flt):
                c.stop(timeout=timeout)

            self.__retry_docker_obj_prune(
                obj=self._client.containers, filters=flt
            )
            self.__retry_docker_obj_prune(
                obj=self._client.volumes, filters=flt
            )
        except ConnectionError:
            raise RuntimeError("Could not connect to worker.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_and_cleanup()

    def _pull_images(self):
        if self._exec_image_sha256 not in [
            img.id for img in self._client.images.list()
        ]:
            with self._exec_image.open("rb") as f:
                self._client.images.load(f)


class Executor(DockerConnection):
    def __init__(
        self,
        *args,
        input_files: Tuple[File, ...],
        results_file: Path,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._input_files = input_files
        self._results_file = results_file
        self._io_image = settings.CONTAINER_EXEC_IO_IMAGE

        self._input_volume = f"{self._job_label}-input"
        self._output_volume = f"{self._job_label}-output"

    def execute(self) -> dict:
        self._pull_images()
        self._create_io_volumes()
        self._provision_input_volume()
        self._chmod_volumes()
        self._execute_container()
        return self._get_result()

    def _pull_images(self):
        super()._pull_images()
        self._client.images.pull(repository=self._io_image)

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(name=volume, labels=self._labels)

    def _provision_input_volume(self):
        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._input_volume: {"bind": "/input/", "mode": "rw"}
                    },
                    name=f"{self._job_label}-writer",
                    detach=True,
                    tty=True,
                    labels=self._labels,
                    **self._run_kwargs,
                )
            ) as writer:
                self._copy_input_files(writer=writer)
        except Exception as exc:
            raise RuntimeError(str(exc))

    def _copy_input_files(self, writer):
        for file in self._input_files:
            put_file(
                container=writer,
                src=file,
                dest=f"/input/{Path(file.name).name}",
            )

    def _chmod_volumes(self):
        """Ensure that the i/o directories are writable."""
        try:
            self._client.containers.run(
                image=self._io_image,
                volumes={
                    self._input_volume: {"bind": "/input/", "mode": "rw"},
                    self._output_volume: {"bind": "/output/", "mode": "rw"},
                },
                name=f"{self._job_label}-chmod-volumes",
                command=f"chmod -R 0777 /input/ /output/",
                remove=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        except Exception as exc:
            raise RuntimeError(str(exc))

    def _execute_container(self):
        try:
            self._client.containers.run(
                image=self._exec_image_sha256,
                volumes={
                    self._input_volume: {"bind": "/input/", "mode": "rw"},
                    self._output_volume: {"bind": "/output/", "mode": "rw"},
                },
                name=f"{self._job_label}-executor",
                remove=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        except ContainerError as exc:
            raise RuntimeError(exc.stderr.decode())

    def _get_result(self) -> dict:
        """
        Read and parse the created results file. Due to a bug in the docker
        client, copy the file to memory first rather than cat and read
        stdout.
        """
        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._output_volume: {"bind": "/output/", "mode": "ro"}
                    },
                    name=f"{self._job_label}-reader",
                    detach=True,
                    tty=True,
                    labels=self._labels,
                    **self._run_kwargs,
                )
            ) as reader:
                result = get_file(container=reader, src=self._results_file)
        except NotFound:
            # The container exited without error, but no results file was
            # produced. This shouldn't happen, but does with poorly programmed
            # evaluation containers.
            raise RuntimeError(
                "The evaluation failed for an unknown reason as no results "
                "file was produced. Please contact the organisers for "
                "assistance."
            )
        except Exception as e:
            raise RuntimeError(str(e))

        try:
            result = json.loads(
                result.read().decode(),
                parse_constant=lambda x: None,  # Removes -inf, inf and NaN
            )
        except JSONDecodeError as exc:
            raise RuntimeError(exc.msg)

        return result


class Service(DockerConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Allow networking for service containers
        self._run_kwargs.update(
            {
                "network_disabled": False,
                "network": settings.WORKSTATIONS_NETWORK_NAME,
            }
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Do not cleanup the containers for this job, leave them running."""
        pass

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
        return self._client.containers.get(f"{self._job_label}-service")

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

        traefik_labels = {
            "traefik.enable": "true",
            "traefik.frontend.rule": f"Host:{hostname}",
            "traefik.http.port": str(http_port),
            "traefik.http.frontend.entryPoints": "http",
            "traefik.websocket.port": str(websocket_port),
            "traefik.websocket.frontend.entryPoints": "websocket",
        }

        try:
            self._client.containers.run(
                image=self._exec_image_sha256,
                name=f"{self._job_label}-service",
                remove=True,
                detach=True,
                labels={**self._labels, **traefik_labels},
                environment=environment or {},
                extra_hosts=self.extra_hosts,
                **self._run_kwargs,
            )
        except ContainerError as exc:
            raise RuntimeError(exc.stderr.decode())


@contextmanager
def cleanup(container: ContainerApiMixin):
    """
    Cleans up a docker container which is running in detached mode

    :param container: An instance of a container
    :return:
    """
    try:
        yield container

    finally:
        container.remove(force=True)


def put_file(*, container: ContainerApiMixin, src: File, dest: str) -> ():
    """
    Puts a file on the host into a container.
    This method will create an in memory tar archive, add the src file to this
    and upload it to the docker container where it will be unarchived at dest.

    :param container: The container to write to
    :param src: The path to the source file on the host
    :param dest: The path to the target file in the container
    :return:
    """
    tar_b = io.BytesIO()

    tarinfo = tarfile.TarInfo(name=os.path.basename(dest))
    tarinfo.size = src.size

    with tarfile.open(fileobj=tar_b, mode="w") as tar, src.open("rb") as f:
        tar.addfile(tarinfo, fileobj=f)

    tar_b.seek(0)
    container.put_archive(os.path.dirname(dest), tar_b)


def get_file(*, container: ContainerApiMixin, src: Path):
    tarstrm, info = container.get_archive(src)

    if info["size"] > 2e9:
        raise ValueError(f"File {src} is too big to be decompressed.")

    file_obj = io.BytesIO()
    for ts in tarstrm:
        file_obj.write(ts)

    file_obj.seek(0)
    tar = tarfile.open(mode="r", fileobj=file_obj)
    content = tar.extractfile(src.name)

    return content
