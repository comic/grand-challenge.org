import sys
from json import JSONDecodeError

from dateutil.parser import isoparse
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist

from grandchallenge.components.backends import docker_client
from grandchallenge.components.backends.base import Executor
from grandchallenge.components.backends.docker import (
    DockerConnectionMixin,
    logger,
)
from grandchallenge.components.backends.utils import (
    LOGLINES,
    SourceChoices,
    parse_structured_log,
)


class InsecureDockerExecutor(DockerConnectionMixin, Executor):
    def __init__(self, *args, **kwargs):
        usage_message = (
            "WARNING: The InsecureDockerExecutor is only for development. "
            "Do not use it in a production environment. "
            "Use the SageMakerExecutor instead."
        )

        if settings.DEBUG:
            logger.critical(usage_message)
        elif "pytest" in sys.modules:
            pass
        else:
            raise ImproperlyConfigured(usage_message)

        super().__init__(*args, **kwargs)

    def execute(self):
        self._pull_image()
        self._execute_container()

    def handle_event(self, *, event):
        raise RuntimeError("This backend is not event-driven")

    def deprovision(self):
        super().deprovision()
        docker_client.remove_container(name=self.container_name)

    @staticmethod
    def get_job_name(*, event):
        raise NotImplementedError

    @staticmethod
    def get_job_params(*, job_name):
        raise NotImplementedError

    @property
    def duration(self):
        try:
            details = docker_client.inspect_container(name=self.container_name)
            if details["State"]["Status"] == "exited":
                started_at = details["State"]["StartedAt"]
                finished_at = details["State"]["FinishedAt"]
                return isoparse(finished_at) - isoparse(started_at)
            else:
                return None
        except ObjectDoesNotExist:
            return None

    @property
    def usd_cents_per_hour(self):
        return 100

    @property
    def runtime_metrics(self):
        logger.warning("Runtime metrics are not implemented for this backend")
        return

    def _execute_container(self) -> None:
        environment = {
            **self.invocation_environment,
            "NVIDIA_VISIBLE_DEVICES": settings.COMPONENTS_NVIDIA_VISIBLE_DEVICES,
        }

        if settings.COMPONENTS_DOCKER_TASK_SET_AWS_ENV:
            environment.update(
                {
                    "AWS_ACCESS_KEY_ID": settings.COMPONENTS_DOCKER_TASK_AWS_ACCESS_KEY_ID,
                    "AWS_SECRET_ACCESS_KEY": settings.COMPONENTS_DOCKER_TASK_AWS_SECRET_ACCESS_KEY,
                    "AWS_S3_ENDPOINT_URL": settings.COMPONENTS_S3_ENDPOINT_URL,
                }
            )

        try:
            docker_client.run_container(
                repo_tag=self._exec_image_repo_tag,
                name=self.container_name,
                command=[
                    "invoke",
                    "--file",
                    f"s3://{settings.COMPONENTS_INPUT_BUCKET_NAME}/{self._invocation_key}",
                ],
                labels=self._labels,
                environment=environment,
                network=settings.COMPONENTS_DOCKER_NETWORK_NAME,
                mem_limit=self._memory_limit,
                detach=False,
            )
        finally:
            docker_client.stop_container(name=self.container_name)
            self._set_task_logs()

        self._handle_completed_job()

    def _set_task_logs(self):
        try:
            loglines = docker_client.get_logs(
                name=self.container_name, tail=LOGLINES
            )
        except ObjectDoesNotExist:
            return

        self._parse_loglines(loglines=loglines)

    def _parse_loglines(self, *, loglines):
        stdout = []
        stderr = []

        for line in loglines:
            try:
                timestamp, log = line.replace("\x00", "").split(" ", 1)
                parsed_log = parse_structured_log(log=log)
            except (JSONDecodeError, KeyError, ValueError):
                logger.warning("Could not parse log")
                continue

            if parsed_log is not None:
                output = f"{timestamp} {parsed_log.message}"
                if parsed_log.source == SourceChoices.STDOUT:
                    stdout.append(output)
                elif parsed_log.source == SourceChoices.STDERR:
                    stderr.append(output)
                else:
                    logger.error("Invalid source")

        self._stdout = stdout
        self._stderr = stderr
