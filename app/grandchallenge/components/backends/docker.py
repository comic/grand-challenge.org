import os
from socket import getaddrinfo
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
from grandchallenge.components.backends.docker_client import inspect_container
from grandchallenge.components.backends.utils import LOGLINES


class Service:
    def __init__(
        self,
        container_name: str,
        exec_image_repo_tag: str,
    ):
        super().__init__()
        self._container_name = container_name
        self._exec_image_repo_tag = exec_image_repo_tag

    @property
    def container_name(self):
        return self._container_name

    @property
    def host_address(self):
        docker_hostname = urlparse(os.environ["DOCKER_HOST"]).hostname
        return getaddrinfo(docker_hostname, None)[0][4][0]

    def get_port_mapping(self, port):
        container_info = inspect_container(name=self.container_name)
        return container_info["NetworkSettings"]["Ports"][f"{port}/tcp"][0][
            "HostPort"
        ]

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
        environment: dict,
    ):
        docker_client.run_container(
            repo_tag=self._exec_image_repo_tag,
            name=self.container_name,
            environment=environment,
            ports=[
                settings.COMPONENTS_SERVICE_CONTAINER_HTTP_PORT,
                settings.COMPONENTS_SERVICE_CONTAINER_WEBSOCKET_PORT,
            ],
            mem_limit=settings.COMPONENTS_MEMORY_LIMIT,
        )

    def stop_and_cleanup(self):
        docker_client.stop_container(name=self.container_name)
        docker_client.remove_container(name=self.container_name)
