import json
import multiprocessing
import os
import typing
import uuid
from contextlib import contextmanager
from json import JSONDecodeError

import docker
from celery import shared_task
from django.conf import settings
from django.core.files import File
from docker.api.container import ContainerApiMixin
from docker.errors import ContainerError

from evaluation.exceptions import TimeoutException, MethodContainerError, \
    SubmissionError
from evaluation.models import Job, Result
from evaluation.utils import put_file
from evaluation.widgets.uploader import cleanup_stale_files


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
    def __init__(self, *, job_id: uuid.UUID, input_file: File,
                 eval_image: File, eval_image_id: str):
        super(Evaluator, self).__init__()

        self._job_id = str(job_id)
        self._input_file = input_file
        self._eval_image = eval_image
        self._eval_image_id = eval_image_id

        self._io_image = 'alpine:3.6'
        self._mem_limit = '2g'
        self._cpu_period = 100000
        self._cpu_quota = 25000

        # TODO: error handling
        self._client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

        self._input_volume = f'{self._job_id}-input'
        self._output_volume = f'{self._job_id}-output'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        filter = {'label': f'job_id={self._job_id}'}

        for container in self._client.containers.list(filters=filter):
            container.stop()

        self._client.containers.prune(filters=filter)
        self._client.volumes.prune(filters=filter)

    def evaluate(self) -> dict:
        self._pull_images()
        self._create_io_volumes()
        self._run(target=self._provision_input_volume, timeout=600)
        self._run(target=self._run_evaluation, timeout=3600)
        return self._get_result()

    def _run(self, *, target: typing.Callable, timeout: int = None):
        p = multiprocessing.Process(target=target)

        p.start()
        p.join(timeout)

        if p.is_alive():
            p.terminate()
            raise TimeoutException(f'{target} timed out after {timeout} s.')

    def _pull_images(self):
        if len(self._client.images.list(name=self._io_image)) == 0:
            self._client.images.pull(name=self._io_image)

        if self._eval_image_id not in [x.id for x in
                                       self._client.images.list()]:
            self._eval_image.open('rb')  # No context manager for Django Files
            try:
                self._client.images.load(self._eval_image)
            finally:
                self._eval_image.close()

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(
                name=volume,
                labels={'job_id': self._job_id}
            )

    def _provision_input_volume(self):
        dest_file = '/input/' + os.path.split(self._input_file.name)[1]
        try:
            with cleanup(self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._input_volume: {
                            'bind': '/input/',
                            'mode': 'rw'
                        }
                    },
                    labels={'job_id': self._job_id},
                    detach=True,
                    tty=True,
                    network_disabled=True,
                    mem_limit=self._mem_limit,
                    cpu_period=self._cpu_period,
                    cpu_quota=self._cpu_quota,
            )) as writer:
                put_file(
                    container=writer,
                    src=self._input_file,
                    dest=dest_file
                )

                # Unzip the file in the container rather than in the python
                # process. With resource limits this should provide some
                # protection against zip bombs etc.
                # TODO: Check that the top level directory is not duplicate
                writer.exec_run(f'unzip {dest_file} -d /input')
                writer.exec_run('rm {dest_file}')
        except Exception as exc:
            raise SubmissionError(str(exc))

    def _run_evaluation(self):
        try:
            self._client.containers.run(
                image=self._eval_image_id,
                volumes={
                    self._input_volume: {
                        'bind': '/input/',
                        'mode': 'ro'
                    },
                    self._output_volume: {
                        'bind': '/output/',
                        'mode': 'rw'
                    }
                },
                labels={'job_id': self._job_id},
                network_disabled=True,
                mem_limit=self._mem_limit,
                cpu_period=self._cpu_period,
                cpu_quota=self._cpu_quota,
            )
        except ContainerError as exc:
            raise MethodContainerError(exc.stderr)

    def _get_result(self) -> dict:
        try:
            result = self._client.containers.run(
                image=self._io_image,
                volumes={
                    self._output_volume: {
                        'bind': '/output/',
                        'mode': 'ro'
                    }
                },
                labels={'job_id': self._job_id},
                command='cat /output/metrics.json',
                network_disabled=True,
                mem_limit=self._mem_limit,
                cpu_period=self._cpu_period,
                cpu_quota=self._cpu_quota,
            )
        except ContainerError as exc:
            raise MethodContainerError(exc.stderr)

        try:
            result = json.loads(result.decode())
        except JSONDecodeError as exc:
            raise MethodContainerError(exc.msg)

        return result


@shared_task
def evaluate_submission(*, job_id: uuid.UUID = None, job: Job = None) -> dict:
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
        job = Job.objects.get(id__exact=job_id)  # type: Job

    job.update_status(status=Job.STARTED)

    try:
        with Evaluator(
                job_id=job.id,
                input_file=job.submission.file,
                eval_image=job.method.image,
                eval_image_id=job.method.image_id
        ) as e:
            result = e.evaluate()
    except Exception as exc:
        job.update_status(status=Job.FAILURE, output=str(exc))
        raise exc

    Result.objects.create(
        user=job.submission.user,
        challenge=job.submission.challenge,
        method=job.method,
        metrics=result
    )

    job.update_status(status=Job.SUCCESS)

    return result


@shared_task
def cleanup_stale_uploads(*_):
    cleanup_stale_files()
