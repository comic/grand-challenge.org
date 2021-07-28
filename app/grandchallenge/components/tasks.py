import json
import tarfile
import uuid
from datetime import timedelta
from typing import Dict

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import OperationalError
from django.db.models import DateTimeField, ExpressionWrapper, F
from django.utils.module_loading import import_string
from django.utils.timezone import now

from grandchallenge.components.backends.exceptions import ComponentException
from grandchallenge.components.emails import send_invalid_dockerfile_email
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile


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
        image_sha256 = _validate_docker_image_manifest(
            model=model, instance=instance
        )
        ready = True
    except ValidationError:
        send_invalid_dockerfile_email(container_image=instance)
        image_sha256 = ""
        ready = False

    model.objects.filter(pk=instance.pk).update(
        image_sha256=image_sha256, ready=ready
    )


def _validate_docker_image_manifest(*, model, instance) -> str:
    manifest = _extract_docker_image_file(
        model=model, instance=instance, filename="manifest.json"
    )
    manifest = json.loads(manifest)

    if len(manifest) != 1:
        model.objects.filter(pk=instance.pk).update(
            status=(
                f"The container image file should only have 1 image. "
                f"This file contains {len(manifest)}."
            )
        )
        raise ValidationError("Invalid Dockerfile")

    image_sha256 = manifest[0]["Config"][:64]

    config = _extract_docker_image_file(
        model=model, instance=instance, filename=f"{image_sha256}.json"
    )
    config = json.loads(config)

    if "User" not in config["config"] or str(
        config["config"]["User"].lower()
    ) in ["", "root", "0"]:
        model.objects.filter(pk=instance.pk).update(
            status=(
                "The container runs as root. Please add a user, group and "
                "USER instruction to your Dockerfile, rebuild, test and "
                "upload the container again, see "
                "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user"
            )
        )
        raise ValidationError("Invalid Dockerfile")

    return f"sha256:{image_sha256}"


def _extract_docker_image_file(*, model, instance, filename: str):
    """Extract a file from the root of a tarball."""
    try:
        with instance.image.open(mode="rb") as im, tarfile.open(
            fileobj=im, mode="r"
        ) as t:
            member = dict(zip(t.getnames(), t.getmembers()))[filename]
            file = t.extractfile(member).read()
        return file
    except (KeyError, tarfile.ReadError):
        model.objects.filter(pk=instance.pk).update(
            status=(
                f"{filename} not found at the root of the container image "
                f"file. Was this created with docker save?"
            )
        )
        raise ValidationError("Invalid Dockerfile")


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


def _get_executor_kwargs(*, job):
    return {
        "job_id": str(job.pk),
        "job_class": type(job),
        "input_civs": job.inputs.prefetch_related(
            "interface", "image__files"
        ).all(),
        "input_prefixes": job.input_prefixes,
        "output_interfaces": job.output_interfaces,
        "exec_image": job.container.image,
        "exec_image_sha256": job.container.image_sha256,
        "memory_limit": job.container.requires_memory_gb,
    }


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def provision_job(
    *_,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )

    if job.status in [job.PENDING, job.RETRY]:
        job.update_status(status=job.PROVISIONING)
    else:
        raise RuntimeError("Job is not ready for provisioning")

    try:
        Executor = import_string(backend)  # noqa: N806
        with Executor(**_get_executor_kwargs(job=job)) as ev:
            ev.provision()
    except Exception:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE, error_message="Could not provision resources",
        )
        raise
    else:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(status=job.PROVISIONED)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def execute_job(
    *_,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
) -> None:
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )

    if job.status == job.PROVISIONED:
        job.update_status(status=job.EXECUTING)
    else:
        raise RuntimeError("Job is not set to be executed")

    if not job.container.ready:
        msg = f"Method {job.container.pk} was not ready to be used"
        job.update_status(status=job.FAILURE, error_message=msg)
        raise RuntimeError(msg)
    try:
        Executor = import_string(backend)  # noqa: N806
        with Executor(**_get_executor_kwargs(job=job)) as ev:
            # This call is potentially very long
            ev.execute()
    except ComponentException as e:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=ev.stdout,
            stderr=ev.stderr,
            error_message=str(e),
        )
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=ev.stdout,
            stderr=ev.stderr,
            error_message="Time limit exceeded",
        )
    except Exception:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE,
            stdout=ev.stdout,
            stderr=ev.stderr,
            error_message="An unexpected error occurred",
        )
        raise
    else:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.EXECUTED, stdout=ev.stdout, stderr=ev.stderr
        )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def parse_job_outputs(
    *_,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )

    if job.status == job.EXECUTED or job.outputs.exists():
        job.update_status(status=job.PARSING)
    else:
        raise RuntimeError("Job is not ready for output parsing")

    try:
        Executor = import_string(backend)  # noqa: N806
        with Executor(**_get_executor_kwargs(job=job)) as ev:
            ev.get_outputs()
    except ComponentException as e:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE, error_message=str(e),
        )
    except Exception:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.update_status(
            status=job.FAILURE, error_message="Could not parse outputs",
        )
        raise
    else:
        job = get_model_instance(
            pk=job_pk, app_label=job_app_label, model_name=job_model_name
        )
        job.outputs.add(*ev.outputs)
        job.update_status(status=job.SUCCESS)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def deprovision_job(
    *_,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )

    if job.status not in [job.PROVISIONED, job.SUCCESS, job.FAILURE]:
        raise RuntimeError("Job is not ready for deprovisioning")

    Executor = import_string(backend)  # noqa: N806
    with Executor(**_get_executor_kwargs(job=job)) as ev:
        ev.deprovision()


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
