import logging
from ipaddress import ip_address
from json import JSONDecodeError
from pathlib import Path
from socket import getaddrinfo
from tempfile import TemporaryDirectory

import requests
from dateutil.parser import isoparse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import (
    LOGLINES,
    SourceChoices,
    parse_structured_log,
    user_error,
)
from grandchallenge.components.tasks import _repo_login_and_run

logger = logging.getLogger(__name__)


class DockerConnectionMixin:
    @property
    def container_name(self):
        return self._job_id

    @property
    def _labels(self):
        return {"job": f"{self._job_id}", "traefik.enable": "false"}

    def _pull_image(self):
        try:
            docker_client.get_image(repo_tag=self._exec_image_repo_tag)
        except ObjectDoesNotExist:
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
                    docker_client.load_image(input=tarball)
            else:
                docker_client.pull_image(
                    repo_tag=self._exec_image_repo_tag, authenticate=True
                )


class DockerExecutor(DockerConnectionMixin, Executor):
    def execute(self, *, input_civs, input_prefixes):
        self._pull_image()
        self._execute_container(
            input_civs=input_civs, input_prefixes=input_prefixes
        )

    def deprovision(self):
        super().deprovision()
        docker_client.remove_container(name=self.container_name)

    @staticmethod
    def get_job_params(*, event):
        raise NotImplementedError

    @property
    def duration(self):
        try:
            details = docker_client.inspect_container(name=self.container_name)
            if details["State"]["Status"] == "exited":
                started_at = details["State"]["StartedAt"]
                finished_at = details["State"]["FinishedAt"]
                return isoparse(finished_at) - isoparse(started_at)
            else:
                return None
        except ObjectDoesNotExist:
            return None

    @property
    def runtime_metrics(self):
        logger.warning("Runtime metrics are not implemented for this backend")
        return

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

        try:
            docker_client.run_container(
                repo_tag=self._exec_image_repo_tag,
                name=self.container_name,
                command=["serve"],
                labels=self._labels,
                environment=environment,
                network=settings.COMPONENTS_DOCKER_NETWORK_NAME,
                mem_limit=self._memory_limit,
            )
            self._await_container_ready()
            try:
                response = requests.post(
                    f"http://{self.container_name}:8080/invocations",
                    json=self._get_invocation_json(
                        input_civs=input_civs, input_prefixes=input_prefixes
                    ),
                    timeout=self._time_limit,
                )
            except requests.exceptions.Timeout:
                raise ComponentException("Time limit exceeded")
        finally:
            docker_client.stop_container(name=self.container_name)
            self._set_task_logs()

        response = response.json()
        exit_code = int(response["return_code"])

        if exit_code == 137:
            raise ComponentException(
                "The container was killed as it exceeded the memory limit "
                f"of {self._memory_limit}g."
            )
        elif exit_code != 0:
            raise ComponentException(user_error(self.stderr))

    def _await_container_ready(self):
        attempts = 0
        while True:
            attempts += 1

            try:
                # Timeout is from the SageMaker API definitions
                # https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-batch-code.html#your-algorithms-batch-algo-ping-requests
                response = requests.get(
                    f"http://{self.container_name}:8080/ping",
                    timeout=2,
                )
            except requests.exceptions.RequestException:
                continue

            if response.status_code == 200:
                break
            elif attempts > 10:
                raise ComponentException("Container did not start in time")

    def _set_task_logs(self):
        try:
            loglines = docker_client.get_logs(
                name=self.container_name, tail=LOGLINES
            )
        except ObjectDoesNotExist:
            return

        self._parse_loglines(loglines=loglines)

    def _parse_loglines(self, *, loglines):
        stdout = []
        stderr = []

        for line in loglines:
            try:
                timestamp, log = line.replace("\x00", "").split(" ", 1)
                parsed_log = parse_structured_log(log=log)
            except (JSONDecodeError, KeyError, ValueError):
                logger.error("Could not parse log")
                continue

            if parsed_log is not None:
                output = f"{timestamp} {parsed_log.message}"
                if parsed_log.source == SourceChoices.STDOUT:
                    stdout.append(output)
                elif parsed_log.source == SourceChoices.STDERR:
                    stderr.append(output)
                else:
                    logger.error("Invalid source")

        self._stdout = stdout
        self._stderr = stderr


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
    def extra_hosts(self):
        if settings.DEBUG:
            # The workstation needs to communicate with the django api. In
            # production this happens automatically via the external DNS, but
            # when running in debug mode we need to pass through the developers
            # host via the workstations network gateway

            network = docker_client.inspect_network(
                name=settings.WORKSTATIONS_NETWORK_NAME
            )

            return {"gc.localhost": network["IPAM"]["Config"][0]["Gateway"]}
        else:
            return {}

    def logs(self) -> str:
        """Get the container logs for this service."""
        try:
            logs = docker_client.get_logs(
                name=self.container_name, tail=LOGLINES
            )
            return "\n".join(logs)
        except ObjectDoesNotExist:
            return ""

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

        docker_client.run_container(
            repo_tag=self._exec_image_repo_tag,
            name=self.container_name,
            remove=True,
            labels={**self._labels, **traefik_labels},
            environment=environment or {},
            extra_hosts=self.extra_hosts,
            ports=ports,
            network=settings.WORKSTATIONS_NETWORK_NAME,
            mem_limit=self._memory_limit,
        )

    def stop_and_cleanup(self):
        docker_client.stop_container(name=self.container_name)
        docker_client.remove_container(name=self.container_name)
