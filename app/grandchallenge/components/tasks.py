import base64
import json
import subprocess
import tarfile
import uuid
from datetime import timedelta
from tempfile import NamedTemporaryFile
from typing import Dict

import boto3
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import OperationalError
from django.db.models import DateTimeField, ExpressionWrapper, F
from django.utils.timezone import now

from grandchallenge.components.backends.exceptions import (
    ComponentException,
    RetryStep,
)
from grandchallenge.components.emails import send_invalid_dockerfile_email
from grandchallenge.components.exceptions import PriorStepFailed
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile

RETRY_INTERVAL_SECONDS = 30
RETRY_DURATION_DAYS = 2


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def validate_docker_image(*, pk: uuid.UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if not instance.image:
        if instance.staged_image_uuid:
            # Create the image from the staged file
            uploaded_image = StagedAjaxFile(instance.staged_image_uuid)
            with uploaded_image.open() as f:
                instance.image.save(uploaded_image.name, File(f))
        else:
            # No image to validate
            return

    try:
        image_sha256 = _validate_docker_image_manifest(instance=instance)
    except ValidationError as e:
        model.objects.filter(pk=instance.pk).update(
            image_sha256="", ready=False, status=oxford_comma(e)
        )
        send_invalid_dockerfile_email(container_image=instance)
        return

    push_container_image(instance=instance)
    model.objects.filter(pk=instance.pk).update(
        image_sha256=image_sha256, ready=True
    )


def push_container_image(*, instance):
    with NamedTemporaryFile(suffix=".tar") as o:
        with instance.image.open(mode="rb") as im:
            # Rewrite to tar as crane cannot handle gz
            _decompress_tarball(in_fileobj=im, out_fileobj=o)

        login_cmd = _get_repo_login_cmd()
        push_cmd = f"crane push {o.name} {instance.repo_tag}"

        if settings.COMPONENTS_REGISTRY_INSECURE:
            # Note, not setting this on login_cmd as it should never happen
            push_cmd += " --insecure"

        if login_cmd:
            cmd = f"{login_cmd} && {push_cmd}"
        else:
            cmd = push_cmd

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Could not push image: {e.stdout.decode()}")


def _get_repo_login_cmd():
    if settings.COMPONENTS_REGISTRY_INSECURE:
        # Do not login to insecure registries
        return ""
    else:
        user, token = _get_ecr_user_and_token()
        return f"crane auth login {settings.COMPONENTS_REGISTRY_URL} -u {user} -p {token}"


def _get_ecr_user_and_token():
    client = boto3.client("ecr")
    auth = client.get_authorization_token()

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ecr.html#ECR.Client.get_authorization_token
    b64_user_token = auth["authorizationData"][0]["authorizationToken"]
    b64_user_token_bytes = b64_user_token.encode("ascii")
    user_token = base64.b64decode(b64_user_token_bytes).decode("ascii")
    user, token = user_token.split(":")

    return user, token


def _decompress_tarball(*, in_fileobj, out_fileobj):
    """Create an uncompress tarball from a (compressed) tarball"""
    with tarfile.open(fileobj=in_fileobj, mode="r") as it, tarfile.open(
        fileobj=out_fileobj, mode="w|"
    ) as ot:
        for member in it.getmembers():
            extracted = it.extractfile(member)
            ot.addfile(member, extracted)


def _validate_docker_image_manifest(*, instance) -> str:
    manifest = _extract_docker_image_file(
        instance=instance, filename="manifest.json"
    )
    manifest = json.loads(manifest)

    if len(manifest) != 1:
        raise ValidationError(
            f"The container image file should only have 1 image. "
            f"This file contains {len(manifest)}."
        )

    image_sha256 = manifest[0]["Config"][:64]

    config = _extract_docker_image_file(
        instance=instance, filename=f"{image_sha256}.json"
    )
    config = json.loads(config)

    user = str(config["config"].get("User", "")).lower()

    if (
        user in ["", "root", "0"]
        or user.startswith("0:")
        or user.startswith("root:")
    ):
        raise ValidationError(
            "The container runs as root. Please add a user, group and "
            "USER instruction to your Dockerfile, rebuild, test and "
            "upload the container again, see "
            "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user"
        )

    return f"sha256:{image_sha256}"


def _extract_docker_image_file(*, instance, filename: str):
    """Extract a file from the root of a tarball."""
    try:
        with instance.image.open(mode="rb") as im, tarfile.open(
            fileobj=im, mode="r"
        ) as t:
            member = dict(zip(t.getnames(), t.getmembers()))[filename]
            file = t.extractfile(member).read()
        return file
    except (KeyError, tarfile.ReadError):
        raise ValidationError(
            f"{filename} not found at the root of the container image "
            f"file. Was this created with docker save?"
        )


def retry_if_dropped(func):
    """
    Retry a function that relies on an open database connection.

    Use this decorator when you have a long running task as sometimes the db
    connection will drop.
    """

    def wrapper(*args, **kwargs):
        n_tries = 0
        max_tries = 2
        err = None

        while n_tries < max_tries:
            n_tries += 1

            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                err = e

                # This needs to be a local import
                from django.db import connection

                connection.close()

        raise err

    return wrapper


@retry_if_dropped
def get_model_instance(*, pk, app_label, model_name):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    return model.objects.get(pk=pk)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def provision_job(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status in [job.PENDING, job.RETRY]:
        job.update_status(status=job.PROVISIONING)
    else:
        raise PriorStepFailed("Job is not ready for provisioning")

    try:
        executor.provision(
            input_civs=job.inputs.prefetch_related(
                "interface", "image__files"
            ).all(),
            input_prefixes=job.input_prefixes,
        )
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="Could not provision resources",
        )
        executor.deprovision()
        raise
    else:
        job.update_status(status=job.PROVISIONED)


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"], bind=True
)
def execute_job(
    self,
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    """
    Executes the component job, can block with some backends.

    `execute_job` can raise `ComponentException` in which case
    the job will be marked as failed and the error returned to the user.

    Job must be in the PROVISIONED state.

    Once the job has executed it will be in the EXECUTING or FAILURE states.
    """
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status == job.PROVISIONED:
        job.update_status(status=job.EXECUTING)
    else:
        executor.deprovision()
        raise PriorStepFailed("Job is not set to be executed")

    if not job.container.ready:
        msg = f"Method {job.container.pk} was not ready to be used"
        job.update_status(status=job.FAILURE, error_message=msg)
        executor.deprovision()
        raise PriorStepFailed(msg)

    try:
        # This call is potentially very long
        executor.execute()
    except RetryStep:
        job.update_status(status=job.PROVISIONED)
        try:
            self.retry(
                countdown=RETRY_INTERVAL_SECONDS,
                max_retries=3600
                * 24
                * RETRY_DURATION_DAYS
                / RETRY_INTERVAL_SECONDS,
            )
        except MaxRetriesExceededError:
            job.update_status(
                status=job.FAILURE,
                stdout=executor.stdout,
                stderr=executor.stderr,
                error_message="Time limit exceeded",
            )
            executor.deprovision()
            raise
    except ComponentException as e:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message=str(e),
        )
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message="Time limit exceeded",
        )
    except Exception:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message="An unexpected error occurred",
        )
        executor.deprovision()
        raise


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"], bind=True
)
def await_job_completion(
    self,
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    """
    Waits for the job to complete and sets stdout and stderr.
    `await_completion` is expected to raise `RetryStep` in which
    case the job will be requeued, or `ComponentException` in which case
    the job will be marked as failed and the error returned to the user.

    Job must be in the EXECUTING state.

    Once the job has executed it will be in the EXECUTED or FAILURE states.
    """
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTING:
        executor.deprovision()
        raise PriorStepFailed("Job is not executing")

    try:
        executor.await_completion()
    except RetryStep:
        try:
            self.retry(
                countdown=RETRY_INTERVAL_SECONDS,
                max_retries=3600
                * 24
                * RETRY_DURATION_DAYS
                / RETRY_INTERVAL_SECONDS,
            )
        except MaxRetriesExceededError:
            job.update_status(
                status=job.FAILURE,
                stdout=executor.stdout,
                stderr=executor.stderr,
                error_message="Time limit exceeded",
            )
            executor.deprovision()
            raise
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message=str(e),
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message="An unexpected error occurred",
        )
        executor.deprovision()
        raise
    else:
        job.update_status(
            status=job.EXECUTED,
            stdout=executor.stdout,
            stderr=executor.stderr,
            duration=executor.duration,
        )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def parse_job_outputs(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status == job.EXECUTED and not job.outputs.exists():
        job.update_status(status=job.PARSING)
    else:
        executor.deprovision()
        raise PriorStepFailed("Job is not ready for output parsing")

    try:
        outputs = executor.get_outputs(
            output_interfaces=job.output_interfaces.all()
        )
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE, error_message=str(e),
        )
        raise PriorStepFailed("Could not parse outputs")
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="Could not parse outputs",
        )
        raise
    else:
        job.outputs.add(*outputs)
        job.update_status(status=job.SUCCESS)
    finally:
        executor.deprovision()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def deprovision(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    """Task that can be called manually in case of errors"""
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)
    executor.deprovision()


@shared_task
def mark_long_running_jobs_failed(
    *, app_label: str, model_name: str, extra_filters: Dict[str, str] = None
):
    """
    Mark jobs that have been started but did not finish (maybe due to
    an unrecoverable hardware error). It will mark tasks FAILED that have the
    status STARTED after 1.2x the task limit (which is different for each
    queue), so, this must be scheduled on the same queue that the execute_job
    task is run for this app_label and model_name.

    If the task is still running on Celery then it will still be able to
    report as passed later.
    """
    Job = apps.get_model(  # noqa: N806
        app_label=app_label, model_name=model_name
    )

    jobs_to_mark = Job.objects.filter(
        started_at__lt=now()
        - 1.2 * timedelta(seconds=settings.CELERY_TASK_TIME_LIMIT),
        status=Job.EXECUTING,
    )

    if extra_filters:
        jobs_to_mark = jobs_to_mark.filter(**extra_filters)

    for j in jobs_to_mark:
        j.update_status(
            status=Job.FAILURE, error_message="Time limit exceeded."
        )

    return [j.pk for j in jobs_to_mark]


@shared_task
def start_service(*, pk: uuid.UUID, app_label: str, model_name: str):
    session = get_model_instance(
        pk=pk, app_label=app_label, model_name=model_name
    )
    session.start()


@shared_task
def stop_service(*, pk: uuid.UUID, app_label: str, model_name: str):
    session = get_model_instance(
        pk=pk, app_label=app_label, model_name=model_name
    )
    session.stop()


@shared_task
def stop_expired_services(*, app_label: str, model_name: str, region: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    services_to_stop = (
        model.objects.annotate(
            expires=ExpressionWrapper(
                F("created") + F("maximum_duration"),
                output_field=DateTimeField(),
            )
        )
        .filter(expires__lt=now(), region=region)
        .exclude(status=model.STOPPED)
    )

    for service in services_to_stop:
        service.stop()

    return [str(s) for s in services_to_stop]
