import json
import logging
import os
import shlex
from ipaddress import ip_address
from json import JSONDecodeError
from pathlib import Path
from socket import getaddrinfo
from subprocess import run
from tempfile import TemporaryDirectory

import requests
from dateutil.parser import isoparse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from docker.errors import APIError

from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.backends.utils import (
    LOGLINES,
    SourceChoices,
    parse_structured_log,
    user_error,
)
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.components.tasks import _repo_login_and_run
from grandchallenge.evaluation.utils import get

logger = logging.getLogger(__name__)


class DockerClient:
    def _run(self, *args, authenticate=False):
        clean_command = shlex.join(["docker", *args])

        if authenticate:
            auth_config = _get_registry_auth_config()
            login_command = shlex.join(
                [
                    "docker",
                    "login",
                    "--username",
                    auth_config["username"],
                    "--password",
                    auth_config["password"],
                    settings.COMPONENTS_REGISTRY_URL,
                ]
            )
            clean_command = f"{login_command} && {clean_command}"

        return run(
            ["/bin/sh", "-c", clean_command],
            check=True,
            capture_output=True,
            text=True,
        )

    def pull_image(self, *, repo_tag, authenticate=False):
        return self._run("image", "pull", repo_tag, authenticate=authenticate)

    def build_image(self, *, repo_tag, path):
        return self._run("build", "--tag", repo_tag, path)

    def save_image(self, *, repo_tag, output):
        return self._run("save", "--output", str(output), repo_tag)

    def load_image(self, *, input):
        return self._run("load", "--input", str(input))

    def list_images(self, *, repo_tag=None):
        args = ["image", "list", "--no-trunc", "--format", "{{json .}}"]

        if repo_tag is not None:
            args.append(repo_tag)

        result = self._run(*args)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def get_image(self, *, repo_tag):
        return get(self.list_images(repo_tag=repo_tag))

    def stop_container(self, *, name):
        try:
            container_id = self.get_container_id(name=name)
            return self._run("stop", container_id)
        except ObjectDoesNotExist:
            return

    def remove_container(self, *, name):
        try:
            container_id = self.get_container_id(name=name)
            self._run("rm", container_id)
        except ObjectDoesNotExist:
            return

    def get_container_id(self, *, name):
        result = self._run(
            "ps", "--all", "--quiet", "--filter", f"name={name}"
        )
        return get([line for line in result.stdout.splitlines()])

    def inspect_container(self, *, name):
        container_id = self.get_container_id(name=name)
        result = self._run("inspect", "--format", "{{json .}}", container_id)
        return json.loads(result.stdout.strip())

    def get_logs(self, *, name, tail=None):
        container_id = self.get_container_id(name=name)
        args = ["logs", "--timestamps"]

        if tail is not None:
            args.extend(["--tail", str(tail)])

        result = self._run(*args, container_id)

        return result.stdout.splitlines() + result.stderr.splitlines()

    def run_container(
        self,
        *,
        repo_tag,
        name,
        labels,
        environment,
        network,
        mem_limit,
        ports=None,
        extra_hosts=None,
        command=None,
        remove=False,
    ):
        args = [
            "run",
            "--name",
            name,
            "--network",
            network,
            "--memory",
            f"{mem_limit}g",
            "--memory-swap",
            f"{mem_limit}g",
            "--shm-size",
            f"{settings.COMPONENTS_SHARED_MEMORY_SIZE}m",
            "--cpu-period",
            str(settings.COMPONENTS_CPU_PERIOD),
            "--cpu-quota",
            str(settings.COMPONENTS_CPU_QUOTA),
            "--cpu-shares",
            str(settings.COMPONENTS_CPU_SHARES),
            "--cpuset-cpus",
            self._cpuset_cpus,
            "--cap-drop",
            "all",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(settings.COMPONENTS_PIDS_LIMIT),
            "--log-driver",
            "json-file",
            "--log-opt",
            "max-size=1g",
            "--init",
            "--detach",
        ]

        if remove:
            args.append("--rm")

        if settings.COMPONENTS_DOCKER_RUNTIME is not None:
            args.extend(["--runtime", settings.COMPONENTS_DOCKER_RUNTIME])

        for k, v in labels.items():
            args.extend(["--label", f"{k}={v}"])

        for k, v in environment.items():
            args.extend(["--env", f"{k}={v}"])

        if extra_hosts is not None:
            for k, v in extra_hosts.items():
                args.extend(["--add-host", f"{k}:{v}"])

        if ports is not None:
            for container_port, v in ports.items():
                bind_address, host_port = v
                host_port = "" if host_port is None else host_port
                args.extend(
                    [
                        "--publish",
                        f"{bind_address}:{host_port}:{container_port}",
                    ]
                )

        # Last two args must be the repo tag and optional command
        args.append(repo_tag)
        if command is not None:
            args.extend(command)

        return self._run(*args)

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
            self.__client = DockerClient()
        return self.__client

    @property
    def _labels(self):
        return {"job": f"{self._job_id}", "traefik.enable": "false"}

    def _pull_image(self):
        try:
            self._client.get_image(repo_tag=self._exec_image_repo_tag)
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
                    self._client.load_image(input=tarball)
            else:
                self._client.pull_image(
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
        self._client.remove_container(name=self.container_name)

    @staticmethod
    def get_job_params(*, event):
        raise NotImplementedError

    @property
    def duration(self):
        try:
            details = self._client.inspect_container(name=self.container_name)
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
            self._client.run_container(
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
            self._client.stop_container(name=self.container_name)
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
        stdout = []
        stderr = []

        try:
            loglines = self._client.get_logs(
                name=self.container_name, tail=LOGLINES
            )
        except ObjectDoesNotExist:
            return

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

        self._client.run_container(
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
