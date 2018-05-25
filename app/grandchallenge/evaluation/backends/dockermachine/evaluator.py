import json
import uuid
from json import JSONDecodeError

import docker
from django.conf import settings
from django.core.files import File
from docker.errors import ContainerError

from grandchallenge.evaluation.backends.dockermachine.utils import (
    cleanup, put_file,
)
from grandchallenge.evaluation.exceptions import (
    SubmissionError, MethodContainerError,
)
from grandchallenge.evaluation.validators import get_file_mimetype


class Evaluator(object):

    def __init__(
        self,
        *,
        job_id: uuid.UUID,
        input_file: File,
        eval_image: File,
        eval_image_sha256: str,
    ):
        super(Evaluator, self).__init__()
        self._job_id = str(job_id)
        self._input_file = input_file
        self._eval_image = eval_image
        self._eval_image_sha256 = eval_image_sha256
        self._io_image = 'alpine:3.6'
        self._mem_limit = '2g'
        self._cpu_period = 100000
        self._cpu_quota = 100000
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
        self._provision_input_volume()
        self._run_evaluation()
        return self._get_result()

    def _pull_images(self):
        if len(self._client.images.list(name=self._io_image)) == 0:
            self._client.images.pull(repository=self._io_image)
        if self._eval_image_sha256 not in [
            x.id for x in self._client.images.list()
        ]:
            self._eval_image.open('rb')  # No context manager for Django Files
            try:
                self._client.images.load(self._eval_image)
            finally:
                self._eval_image.close()

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(
                name=volume, labels={'job_id': self._job_id}
            )

    def _provision_input_volume(self):
        dest_file = '/tmp/submission-src'
        try:
            with cleanup(
                self._client.containers.run(
                    image=self._io_image,
                    volumes={
                        self._input_volume: {'bind': '/input/', 'mode': 'rw'}
                    },
                    labels={'job_id': self._job_id},
                    detach=True,
                    tty=True,
                    network_disabled=True,
                    mem_limit=self._mem_limit,
                    cpu_period=self._cpu_period,
                    cpu_quota=self._cpu_quota,
                )
            ) as writer:
                put_file(
                    container=writer, src=self._input_file, dest=dest_file
                )
                try:
                    self._input_file.open('rb')
                    mimetype = get_file_mimetype(self._input_file)
                finally:
                    self._input_file.close()
                if mimetype.lower() == 'application/zip':
                    # Unzip the file in the container rather than in the python
                    # process. With resource limits this should provide some
                    # protection against zip bombs etc.
                    writer.exec_run(f'unzip {dest_file} -d /input/')
                else:
                    # Not a zip file, so must be a csv
                    writer.exec_run(f'mv {dest_file} /input/submission.csv')
        except Exception as exc:
            raise SubmissionError(str(exc))

    def _run_evaluation(self):
        try:
            self._client.containers.run(
                image=self._eval_image_sha256,
                volumes={
                    self._input_volume: {'bind': '/input/', 'mode': 'ro'},
                    self._output_volume: {'bind': '/output/', 'mode': 'rw'},
                },
                labels={'job_id': self._job_id},
                network_disabled=True,
                mem_limit=self._mem_limit,
                cpu_period=self._cpu_period,
                cpu_quota=self._cpu_quota,
            )
        except ContainerError as exc:
            raise MethodContainerError(exc.stderr.decode())

    def _get_result(self) -> dict:
        try:
            result = self._client.containers.run(
                image=self._io_image,
                volumes={
                    self._output_volume: {'bind': '/output/', 'mode': 'ro'}
                },
                labels={'job_id': self._job_id},
                command='cat /output/metrics.json',
                network_disabled=True,
                mem_limit=self._mem_limit,
                cpu_period=self._cpu_period,
                cpu_quota=self._cpu_quota,
            )
        except ContainerError as exc:
            raise MethodContainerError(exc.stderr.decode())

        try:
            result = json.loads(result.decode())
        except JSONDecodeError as exc:
            raise MethodContainerError(exc.msg)

        return result
