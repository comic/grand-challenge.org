from contextlib import contextmanager

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
    def __init__(self, *, job_id: str):
        super(Evaluator, self).__init__()

        self.__job_id = job_id
        self.__client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

        self.__input_volume = f'{self.__job_id}-input'
        self.__output_volume = f'{self.__job_id}-output'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def evaluate(self):
        self.__pull_images()
        self.__create_io_volumes()
        self.__provision_input_volume()
        return self.__client.containers.run('alpine', 'echo hello world')

    def __pull_images(self):
        for image in ['alpine']:
            self.__client.images.pull(name=image)

    def __create_io_volumes(self):
        for volume in [self.__input_volume, self.__output_volume]:
            self.__client.volumes.create(
                name=volume,
                labels={'job_id': self.__job_id}
            )

    def __provision_input_volume(self):
        with cleanup(self.__client.containers.run(
                image='alpine',
                volumes={
                    self.__input_volume: {
                        'bind': '/input/',
                        'mode': 'rw'
                    }
                },
                detach=True)) as writer:
            pass


@shared_task
def evaluate_submission(*, job_id: str):
    result = Evaluator(job_id=job_id).evaluate()
    return result.decode()
