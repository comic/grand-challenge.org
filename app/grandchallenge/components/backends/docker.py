import logging

from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
from grandchallenge.components.backends.utils import LOGLINES

logger = logging.getLogger(__name__)


class Service:
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
    def container_name(self):
        return self._job_id

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
        environment: dict,
    ):
        if "." in hostname:
            raise ValueError("Hostname cannot contain a '.'")

        labels = {
            "job": f"{self._job_id}",
        }

        docker_client.run_container(
            repo_tag=self._exec_image_repo_tag,
            name=self.container_name,
            labels=labels,
            environment=environment,
            ports=[http_port, websocket_port],
            mem_limit=self._memory_limit,
        )

    def stop_and_cleanup(self):
        docker_client.stop_container(name=self.container_name)
        docker_client.remove_container(name=self.container_name)
