import os
import uuid
from contextlib import contextmanager

import docker
from celery import shared_task
from django.conf import settings
from django.core.files import File
from docker.api.container import ContainerApiMixin

from evaluation.models import Job
from evaluation.utils import put_file


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
    def __init__(self, *, job_id: uuid.UUID, input_file: File):
        super(Evaluator, self).__init__()

        self._job_id = str(job_id)
        self._input_file = input_file

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
                labels={'job_id': self._job_id}
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
            put_file(container=writer, src=self._input_file,
                     dest='/input/' + os.path.split(self._input_file.name)[1])


@shared_task
def evaluate_submission(*, job_id: uuid.UUID = None, job: Job = None):
    """
    Interfaces between Django and the Evaluation. Gathers together all
    resources, and then writes the result back to the database so that the
    Evaluation is only concerned with producing metrics.json.

    :param job_id:
        The id of the job. This must be a str or UUID as celery cannot
        serialise Job objects to JSON.
    :return:
    """

    if (job_id is None and job is None) or (
                    job_id is not None and job is not None):
        raise TypeError('You need to provide either a job or a job_id as '
                        'arguments to evaluate_submission, not none or both.')

    if job_id:
        job = Job.objects.get(id__exact=job_id)

    result = Evaluator(job_id=job.id,
                       input_file=job.submission.file).evaluate()
    return result.decode()
