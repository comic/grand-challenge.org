import itertools
import json
import logging
import os
import shlex
import subprocess
import tarfile
import uuid
from base64 import b64encode
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import OperationalError, transaction
from django.db.models import DateTimeField, ExpressionWrapper, F
from django.db.transaction import on_commit
from django.utils.module_loading import import_string
from django.utils.timezone import now

from grandchallenge.algorithms.exceptions import ImageImportError
from grandchallenge.cases.models import RawImageUploadSession
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    EventError,
    RetryStep,
    TaskCancelled,
    TaskStillExecuting,
)
from grandchallenge.components.emails import send_invalid_dockerfile_email
from grandchallenge.components.exceptions import PriorStepFailed
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma

logger = logging.getLogger(__name__)

MAX_RETRIES = 60 * 24  # 1 day assuming 60 seconds delay


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def validate_docker_image(*, pk: uuid.UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if not instance.image:
        if instance.user_upload:
            with transaction.atomic():
                instance.user_upload.copy_object(to_field=instance.image)
                instance.user_upload.delete()
                # Another validation job will be launched to validate this
                return
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

    if settings.COMPONENTS_SHIM_IMAGES:
        shim_container_image(instance=instance)

    model.objects.filter(pk=instance.pk).update(
        image_sha256=image_sha256,
        latest_shimmed_version=instance.latest_shimmed_version,
        ready=True,
    )


def push_container_image(*, instance):
    with NamedTemporaryFile(suffix=".tar") as o:
        with instance.image.open(mode="rb") as im:
            # Rewrite to tar as crane cannot handle gz
            _decompress_tarball(in_fileobj=im, out_fileobj=o)

        _repo_login_and_run(
            command=["crane", "push", o.name, instance.original_repo_tag]
        )


def _repo_login_and_run(*, command):
    """Logs in to a repo and runs a crane command"""
    if settings.COMPONENTS_REGISTRY_INSECURE:
        # Do not login to insecure registries
        command.append("--insecure")
        clean_command = shlex.join(command)
    else:
        auth_config = _get_registry_auth_config()
        login_command = shlex.join(
            [
                "crane",
                "auth",
                "login",
                settings.COMPONENTS_REGISTRY_URL,
                "-u",
                auth_config["username"],
                "-p",
                auth_config["password"],
            ]
        )
        clean_command = f"{login_command} && {shlex.join(command)}"

    return subprocess.run(
        ["/bin/sh", "-c", clean_command], check=True, capture_output=True
    )


def shim_container_image(*, instance):
    """Patches a container image with the SageMaker Shim executable"""

    # Set the new version, so we can then get the value of the new tag.
    # Do not save the instance until the container image has been mutated.
    instance.latest_shimmed_version = os.environ.get(
        "GRAND_CHALLENGE_SAGEMAKER_SHIM_VERSION"
    )
    new_repo_tag = instance.shimmed_repo_tag
    original_repo_tag = instance.original_repo_tag

    original_config = _get_container_image_config(
        original_repo_tag=original_repo_tag
    )
    env_vars = _get_shim_env_vars(original_config=original_config)
    _mutate_container_image(
        original_repo_tag=original_repo_tag,
        new_repo_tag=new_repo_tag,
        version=instance.latest_shimmed_version,
        env_vars=env_vars,
    )


def encode_b64j(*, val):
    """Base64 encode a JSON serialised value"""
    return b64encode(json.dumps(val).encode("utf-8")).decode("utf-8")


def _get_container_image_config(*, original_repo_tag):
    """Get the configuration of an existing container image"""
    output = _repo_login_and_run(
        command=["crane", "config", original_repo_tag]
    )
    return json.loads(output.stdout.decode("utf-8"))


def _get_shim_env_vars(*, original_config):
    """Get the environment variables for a shimmed container image"""
    cmd = original_config["config"].get("Cmd")
    entrypoint = original_config["config"].get("Entrypoint")

    return {
        "GRAND_CHALLENGE_COMPONENT_CMD_B64J": encode_b64j(val=cmd),
        "GRAND_CHALLENGE_COMPONENT_ENTRYPOINT_B64J": encode_b64j(
            val=entrypoint
        ),
    }


def _mutate_container_image(
    *, original_repo_tag, new_repo_tag, version, env_vars
):
    """Add the SageMaker Shim executable to a container image"""
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        new_layer = tmp_path / "sagemaker-shim.tar"

        with tarfile.open(new_layer, "w") as f:

            def _set_root_555_perms(
                tarinfo,
            ):
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.mode = 0o555
                return tarinfo

            f.add(
                name=f"/opt/sagemaker-shim/sagemaker-shim-{version}-Linux-x86_64",
                arcname="/sagemaker-shim",
                filter=_set_root_555_perms,
            )

            for dir in ["/input", "/output", "/tmp"]:
                # /tmp is required by staticx
                tarinfo = tarfile.TarInfo(dir)
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.mode = 0o777
                f.addfile(tarinfo=tarinfo)

        _repo_login_and_run(
            command=[
                "crane",
                "mutate",
                original_repo_tag,
                "--cmd",
                "",
                "--entrypoint",
                "/sagemaker-shim",
                "--tag",
                new_repo_tag,
                "--append",
                str(new_layer),
                *itertools.chain(
                    *[["--env", f"{k}={v}"] for k, v in env_vars.items()]
                ),
            ]
        )


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
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str, backend: str
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
    except ComponentException as e:
        job.update_status(status=job.FAILURE, error_message=str(e))
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="Could not provision resources"
        )
        raise
    else:
        job.update_status(status=job.PROVISIONED)
        on_commit(execute_job.signature(**job.signature_kwargs).apply_async)


def _retry(*, task, signature_kwargs, retries):
    """
    Retry a task using the delay queue

    We need to retry a task with a delay/countdown. There are several problems
    with doing this in Celery (with SQS/Redis).

    - If a countdown is used the delay features of SQS are not used
      https://github.com/celery/kombu/issues/1074
    - A countdown that needs to be done on the worker results backlogs
      https://github.com/celery/celery/issues/2541
    - The backlogs can still occur even if the countdown/eta is set to zero
      https://github.com/celery/celery/issues/6929

    This method is a workaround for these issues, that creates a new task
    and places this on a queue which has DelaySeconds set. The downside
    is that we need to track retries via the kwargs of the task.
    """
    if retries < MAX_RETRIES:
        step = task.signature(**signature_kwargs)
        queue = step.options.get("queue", task.queue)
        step.options["queue"] = f"{queue}-delay"
        step.kwargs["retries"] = retries + 1
        on_commit(step.apply_async)
    else:
        raise MaxRetriesExceededError


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def execute_job(  # noqa: C901
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
    retries: int = 0,
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
        raise PriorStepFailed(msg)

    try:
        # This call is potentially very long
        executor.execute(
            input_civs=job.inputs.prefetch_related(
                "interface", "image__files"
            ).all(),
            input_prefixes=job.input_prefixes,
        )
    except RetryStep:
        job.update_status(status=job.PROVISIONED)
        try:
            _retry(
                task=execute_job,
                signature_kwargs=job.signature_kwargs,
                retries=retries,
            )
            return
        except MaxRetriesExceededError:
            job.update_status(
                status=job.FAILURE,
                stdout=executor.stdout,
                stderr=executor.stderr,
                error_message="Time limit exceeded",
            )
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
        raise
    else:
        if not executor.IS_EVENT_DRIVEN:
            job.update_status(
                status=job.EXECUTED,
                stdout=executor.stdout,
                stderr=executor.stderr,
                duration=executor.duration,
            )
            on_commit(
                parse_job_outputs.signature(**job.signature_kwargs).apply_async
            )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def handle_event(*, event, backend, retries=0):  # noqa: C901
    """
    Receives events when tasks have stops and determines what to do next.
    In the case of transient failure the job could be scheduled again
    on the backend. If the job is complete then sets stdout and stderr.
    `handle_event` is expected to raise `ComponentException` in which case
    the job will be marked as failed and the error returned to the user.

    Job must be in the EXECUTING state.

    Once the job has executed it will be in the EXECUTED or FAILURE states.
    """
    Backend = import_string(backend)  # noqa: N806

    try:
        job_app_label, job_model_name, job_pk = Backend.get_job_params(
            event=event
        )
    except EventError:
        logger.warning("Event not handled by backend")
        return

    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTING:
        executor.deprovision()
        raise PriorStepFailed("Job is not executing")

    try:
        executor.handle_event(event=event)
    except TaskStillExecuting:
        # Nothing to do here, this will be called when it is finished
        return
    except TaskCancelled:
        job.update_status(status=job.CANCELLED)
        return
    except RetryStep:
        try:
            _retry(
                task=handle_event,
                signature_kwargs={
                    "kwargs": {"event": event, "backend": backend}
                },
                retries=retries,
            )
            return
        except MaxRetriesExceededError:
            job.update_status(
                status=job.FAILURE,
                stdout=executor.stdout,
                stderr=executor.stderr,
                error_message="Time limit exceeded",
            )
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
        raise
    else:
        job.update_status(
            status=job.EXECUTED,
            stdout=executor.stdout,
            stderr=executor.stderr,
            duration=executor.duration,
        )
        on_commit(
            parse_job_outputs.signature(**job.signature_kwargs).apply_async
        )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def parse_job_outputs(
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str, backend: str
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
        job.update_status(status=job.FAILURE, error_message=str(e))
        raise PriorStepFailed("Could not parse outputs")
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="Could not parse outputs"
        )
        raise
    else:
        job.outputs.add(*outputs)
        job.update_status(status=job.SUCCESS)


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def deprovision_job(
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str, backend: str
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)
    executor.deprovision()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_filesystem():
    """
    Periodic task that runs to update the underlying filesystem

    Backends could use this for setting throughput limits, cleaning up data,
    etc.
    """
    Backend = import_string(settings.COMPONENTS_DEFAULT_BACKEND)  # noqa: N806
    return Backend.update_filesystem()


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


@shared_task
def add_images_to_component_interface_value(
    *, component_interface_value_pk, upload_session_pk
):
    session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    if session.image_set.count() != 1:
        error_message = "Image imports should result in a single image"
        session.status = RawImageUploadSession.FAILURE
        session.error_message = error_message
        session.save()
        raise ImageImportError(error_message)

    civ = get_model_instance(
        pk=component_interface_value_pk,
        app_label="components",
        model_name="componentinterfacevalue",
    )

    civ.image = session.image_set.get()
    civ.full_clean()
    civ.save()

    civ.image.update_viewer_groups_permissions()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def civ_value_to_file(*, civ_pk):
    with transaction.atomic():
        civ = get_model_instance(
            pk=civ_pk,
            app_label="components",
            model_name="componentinterfacevalue",
        )

        if civ.value is None:
            raise RuntimeError("CIV value is None")

        civ.file = ContentFile(
            json.dumps(civ.value).encode("utf-8"),
            name=Path(civ.interface.relative_path).name,
        )
        civ.value = None
        civ.save()
