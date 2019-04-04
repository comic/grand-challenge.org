import docker
from django.conf import settings

from grandchallenge.container_exec.backends.docker import Service


def test_service_start_cleanup():
    job_id = "12345"
    job_model = "test"
    exec_image = "crccheck/hello-world"
    filters = {"label": f"job={job_model}-{job_id}"}

    dockerclient = docker.DockerClient(
        base_url=settings.CONTAINER_EXEC_DOCKER_BASE_URL
    )
    dockerclient.images.pull(exec_image)

    exec_sha256 = dockerclient.images.get(exec_image).id

    s = Service(
        job_id=job_id,
        job_model=job_model,
        exec_image=None,
        exec_image_sha256=exec_sha256,
    )
    assert len(dockerclient.containers.list(filters=filters)) == 0

    try:
        s.start()
        containers = dockerclient.containers.list(filters=filters)
        assert len(containers) == 1
    finally:
        s.cleanup()
        assert len(dockerclient.containers.list(filters=filters)) == 0
