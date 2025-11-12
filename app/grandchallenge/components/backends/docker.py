import logging
from ipaddress import ip_address
from pathlib import Path
from socket import getaddrinfo
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
from grandchallenge.components.backends.utils import LOGLINES
from grandchallenge.components.tasks import _repo_login_and_run

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

    @property
    def _labels(self):
        return {"job": f"{self._job_id}", "traefik.enable": "false"}

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
            host_docker_internal = network["IPAM"]["Config"][0]["Gateway"]

            return {
                "gc.localhost": host_docker_internal,
                "garage.localhost": host_docker_internal,
            }
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

    def _pull_image(self):
        try:
            docker_client.inspect_image(repo_tag=self._exec_image_repo_tag)
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

    def stop_and_cleanup(self):
        docker_client.stop_container(name=self.container_name)
        docker_client.remove_container(name=self.container_name)
