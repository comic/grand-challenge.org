from time import sleep

import docker
from django.conf import settings

from grandchallenge.container_exec.backends.docker import Service


def test_service_start_cleanup():
    job_id = "12345"
    job_model = "test"

    dockerclient = docker.DockerClient(
        base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
    )
    filters = {"label": f"job={job_model}-{job_id}"}

    s = Service(
        job_id=job_id,
        job_model=job_model,
        exec_image=settings.CONTAINER_EXEC_IO_IMAGE,
        exec_image_sha256=settings.CONTAINER_EXEC_IO_SHA256,
    )
    assert len(dockerclient.containers.list(filters=filters)) == 0

    s.start()
    # Small sleep here - if a tty is not attached to the alpine container then
    # it will exit straight away
    sleep(0.5)
    assert len(dockerclient.containers.list(filters=filters)) == 1

    s.cleanup(timeout=0)
    assert len(dockerclient.containers.list(filters=filters)) == 0
