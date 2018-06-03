import json
import uuid
from json import JSONDecodeError
from pathlib import Path

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
            results_file: Path = Path("/output/metrics.json"),
    ):
        super().__init__()
        self._job_id = str(job_id)
        self._input_file = input_file
        self._eval_image = eval_image
        self._eval_image_sha256 = eval_image_sha256
        self._io_image = 'alpine:3.6'
        self._results_file = results_file

        self._client = docker.DockerClient(base_url=settings.DOCKER_BASE_URL)

        self._input_volume = f'{self._job_id}-input'
        self._output_volume = f'{self._job_id}-output'

        self._run_kwargs = {
            'labels': {'job_id': self._job_id},
            'network_disabled': True,
            'mem_limit': '2g',
            'cpu_period': 100000,
            'cpu_quota': 100000,
        }

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
        self._client.images.pull(repository=self._io_image)

        if self._eval_image_sha256 not in [
            img.id for img in self._client.images.list()
        ]:
            with self._eval_image.open('rb') as f:
                self._client.images.load(f)

    def _create_io_volumes(self):
        for volume in [self._input_volume, self._output_volume]:
            self._client.volumes.create(
                name=volume, labels=self._run_kwargs["labels"],
            )

    def _provision_input_volume(self):
        dest_file = '/tmp/submission-src'
        try:
            with cleanup(
                    self._client.containers.run(
                        image=self._io_image,
                        volumes={
                            self._input_volume: {
                                'bind': '/input/', 'mode': 'rw'
                            }
                        },
                        detach=True,
                        tty=True,
                        **self._run_kwargs,
                    )
            ) as writer:
                put_file(
                    container=writer, src=self._input_file, dest=dest_file
                )

                with self._input_file.open('rb') as f:
                    mimetype = get_file_mimetype(f)

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
                **self._run_kwargs,
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
                command=f"cat {self._results_file}",
                **self._run_kwargs,
            )
        except ContainerError as exc:
            raise MethodContainerError(exc.stderr.decode())

        try:
            result = json.loads(result.decode())
        except JSONDecodeError as exc:
            raise MethodContainerError(exc.msg)

        return result
