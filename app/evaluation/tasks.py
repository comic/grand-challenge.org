from contextlib import contextmanager
import uuid
import docker
from celery import shared_task
from django.conf import settings
from docker.api.container import ContainerApiMixin


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
        container.stop()
        container.remove(force=True)


class Evaluator(object):
    def __init__(self, *, job_id: uuid.UUID):
        super(Evaluator, self).__init__()

        self._job_id = job_id
        self._client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

        self._input_volume = f'{self._job_id}-input'
        self._output_volume = f'{self._job_id}-output'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def evaluate(self):
        self._pull_images()
        self._create_io_volumes()
        self._provision_input_volume()
        return self._client.containers.run('alpine', 'echo hello world')

    def _pull_images(self):
        for image in ['alpine']:
            self._client.images.pull(name=image)

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(
                name=volume,
                labels={'job_id': self.__job_id}
            )

    def _provision_input_volume(self):
        with cleanup(self._client.containers.run(
                image='alpine',
                volumes={
                    self._input_volume: {
                        'bind': '/input/',
                        'mode': 'rw'
                    }
                },
                detach=True)) as writer:
            pass


@shared_task
def evaluate_submission(*, job_id: uuid.UUID):
    result = Evaluator(job_id=job_id).evaluate()
    return result.decode()
