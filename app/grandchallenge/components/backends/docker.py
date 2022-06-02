import json
import logging
import os
from contextlib import contextmanager
from ipaddress import ip_address
from pathlib import Path
from random import randint
from socket import getaddrinfo
from tempfile import TemporaryDirectory
from time import sleep

import docker
from dateutil.parser import isoparse
from django.conf import settings
from docker.api.container import ContainerApiMixin
from docker.errors import APIError, DockerException, ImageNotFound
from docker.tls import TLSConfig
from docker.types import LogConfig
from requests import HTTPError
from requests.exceptions import ChunkedEncodingError

from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import (
    LOGLINES,
    parse_structured_log,
    user_error,
)
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.components.tasks import _repo_login_and_run

logger = logging.getLogger(__name__)


class DockerConnectionMixin:
    """
    Provides a client with a connection to a docker host, provisioned for
    running the container exec_image.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__client = None

    @property
    def container_name(self):
        return self._job_id

    @property
    def container(self):
        return self._client.containers.get(container_id=self.container_name)

    @property
    def _client(self):
        if self.__client is None:
            client_kwargs = {"base_url": settings.COMPONENTS_DOCKER_BASE_URL}

            if settings.COMPONENTS_DOCKER_TLS_VERIFY:
                tlsconfig = TLSConfig(
                    verify=True,
                    client_cert=(
                        settings.COMPONENTS_DOCKER_TLS_CERT,
                        settings.COMPONENTS_DOCKER_TLS_KEY,
                    ),
                    ca_cert=settings.COMPONENTS_DOCKER_CA_CERT,
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
            # Do not disable the network but use an internal network
            "network_disabled": False,
            "network": settings.COMPONENTS_DOCKER_NETWORK_NAME,
            "mem_limit": f"{self._memory_limit}g",
            # Set to the same as mem_limit to avoid using swap
            "memswap_limit": f"{self._memory_limit}g",
            "shm_size": f"{settings.COMPONENTS_SHARED_MEMORY_SIZE}m",
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
                sleep((2**num_retries) + (randint(0, 1000) / 1000))
        else:
            raise e

    def stop_and_cleanup(self, timeout: int = 10):
        """Stops and prunes all containers associated with this job."""
        flt = {"label": f"job={self._job_id}"}

        for c in self._client.containers.list(filters=flt):
            c.stop(timeout=timeout)

        self.__retry_docker_obj_prune(obj=self._client.containers, filters=flt)

    def _pull_image(self):
        try:
            self._client.images.get(name=self._exec_image_repo_tag)
        except ImageNotFound:
            # This can take a long time so increase the default timeout #1330
            old_timeout = self._client.api.timeout
            self._client.api.timeout = 600  # 10 minutes

            if settings.COMPONENTS_REGISTRY_INSECURE:
                # In CI we cannot set the docker daemon to trust the local
                # registry, so pull the container with crane and then load it
                with TemporaryDirectory() as tmp_dir:
                    tarball = Path(tmp_dir) / f"{self._job_id}.tar"
                    _repo_login_and_run(
                        command=[
                            "crane",
                            "pull",
                            self._exec_image_repo_tag,
                            str(tarball),
                        ]
                    )
                    with open(tarball, "rb") as f:
                        self._client.images.load(f)
            else:
                self._client.images.pull(
                    repository=self._exec_image_repo_tag,
                    auth_config=_get_registry_auth_config(),
                )

            self._client.api.timeout = old_timeout


class DockerExecutor(DockerConnectionMixin, Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self._time_limit != settings.CELERY_TASK_TIME_LIMIT:
            logger.warning("Time limits are not implemented in this backend")

    def execute(self, *, input_civs, input_prefixes):
        self._pull_image()
        self._execute_container(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def deprovision(self):
        super().deprovision()
        self.stop_and_cleanup()

    @staticmethod
    def get_job_params(*, event):
        raise NotImplementedError

    @staticmethod
    def parse_logs(logs):
        output = []

        for line in logs.split("\n"):
            try:
                timestamp, log = line.split(" ", 1)
            except ValueError:
                if line:
                    logger.error(f"Could not parse line: {line}")
                continue

            message = parse_structured_log(log=log)

            if message is not None:
                output.append(f"{timestamp} {message}")

        return "\n".join(output)

    @property
    def stdout(self):
        try:
            return self.parse_logs(
                self.container.logs(
                    stdout=True, stderr=False, timestamps=True, tail=LOGLINES
                )
                .replace(b"\x00", b"")
                .decode("utf-8")
            )
        except (DockerException, ChunkedEncodingError) as e:
            # ChunkedEncodingError leaks from docker py
            # https://github.com/docker/docker-py/issues/2696
            logger.warning(f"Could not fetch stdout: {e}")
            return ""

    @property
    def stderr(self):
        try:
            return self.parse_logs(
                self.container.logs(
                    stdout=False, stderr=True, timestamps=True, tail=LOGLINES
                )
                .replace(b"\x00", b"")
                .decode("utf-8")
            )
        except (DockerException, ChunkedEncodingError) as e:
            # ChunkedEncodingError leaks from docker py
            # https://github.com/docker/docker-py/issues/2696
            logger.warning(f"Could not fetch stderr: {e}")
            return ""

    @property
    def duration(self):
        try:
            if self.container.status == "exited":
                state = self._client.api.inspect_container(
                    container=self.container.id
                )
                started_at = state["State"]["StartedAt"]
                finished_at = state["State"]["FinishedAt"]
                return isoparse(finished_at) - isoparse(started_at)
            else:
                return None
        except DockerException as e:
            logger.warning(f"Could not inspect container: {e}")
            return None

    def _execute_container(self, *, input_civs, input_prefixes) -> None:
        environment = {
            "NVIDIA_VISIBLE_DEVICES": settings.COMPONENTS_NVIDIA_VISIBLE_DEVICES
        }

        if settings.COMPONENTS_DOCKER_TASK_SET_AWS_ENV:
            environment.update(
                {
                    "AWS_ACCESS_KEY_ID": settings.COMPONENTS_DOCKER_TASK_AWS_ACCESS_KEY_ID,
                    "AWS_SECRET_ACCESS_KEY": settings.COMPONENTS_DOCKER_TASK_AWS_SECRET_ACCESS_KEY,
                    "AWS_S3_ENDPOINT_URL": settings.AWS_S3_ENDPOINT_URL,
                }
            )

        inputs = []
        for civ in input_civs:
            key, relative_path = self._get_key_and_relative_path(
                civ=civ, input_prefixes=input_prefixes
            )
            inputs.extend(
                [
                    "--input-file",
                    json.dumps(
                        {
                            "relative_path": relative_path,
                            "bucket_name": settings.COMPONENTS_INPUT_BUCKET_NAME,
                            "bucket_key": key,
                            "decompress": civ.decompress,
                        }
                    ),
                ]
            )

        with stop(
            self._client.containers.run(
                image=self._exec_image_repo_tag,
                command=[
                    "invoke",
                    "--pk",
                    self._job_id,
                    *inputs,
                    "--output-bucket-name",
                    settings.COMPONENTS_OUTPUT_BUCKET_NAME,
                    "--output-prefix",
                    self.io_prefix,
                ],
                name=self.container_name,
                detach=True,
                labels=self._labels,
                environment=environment,
                **self._run_kwargs,
            )
        ) as container:
            container_state = container.wait()

        exit_code = int(container_state["StatusCode"])
        if exit_code == 137:
            raise ComponentException(
                "The container was killed as it exceeded the memory limit "
                f"of {self._run_kwargs['mem_limit']}."
            )
        elif exit_code != 0:
            raise ComponentException(user_error(self.stderr))


class Service(DockerConnectionMixin):
    def __init__(
        self,
        job_id: str,
        exec_image_repo_tag: str,
        memory_limit: int,
    ):
        super().__init__()
        self._job_id = job_id
        self._exec_image_repo_tag = exec_image_repo_tag
        self._memory_limit = memory_limit

    @property
    def _run_kwargs(self):
        kwargs = super()._run_kwargs
        # Use a network with external access
        kwargs["network"] = settings.WORKSTATIONS_NETWORK_NAME
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
        self._pull_image()

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

        if settings.COMPONENTS_PUBLISH_PORTS:
            bind_address = settings.COMPONENTS_PORT_ADDRESS
            try:
                ip_address(bind_address)
            except ValueError:
                # Not an IP address, lets look it up
                bind_address = getaddrinfo(bind_address, None)[0][4][0]
            ports = {
                http_port: (bind_address, None),
                websocket_port: (bind_address, None),
            }
        else:
            ports = {}

        self._client.containers.run(
            image=self._exec_image_repo_tag,
            name=self.container_name,
            remove=True,
            detach=True,
            labels={**self._labels, **traefik_labels},
            environment=environment or {},
            extra_hosts=self.extra_hosts,
            ports=ports,
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
