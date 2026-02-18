from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
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
        environment: dict,
    ):
        docker_client.run_container(
            repo_tag=self._exec_image_repo_tag,
            name=self.container_name,
            environment=environment,
            ports=[http_port, websocket_port],
            mem_limit=settings.COMPONENTS_MEMORY_LIMIT,
        )

    def stop_and_cleanup(self):
        docker_client.stop_container(name=self.container_name)
        docker_client.remove_container(name=self.container_name)
