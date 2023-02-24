import itertools
import json
import logging
import shlex
import subprocess
import tarfile
import uuid
import zlib
from base64 import b64encode
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import boto3
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
from panimg.models import SimpleITKImage

from grandchallenge.cases.models import ImageFile, RawImageUploadSession
from grandchallenge.cases.utils import get_sitk_image
from grandchallenge.components.backends.exceptions import (
    ComponentException,
    RetryStep,
    RetryTask,
    TaskCancelled,
)
from grandchallenge.components.backends.utils import get_sagemaker_model_name
from grandchallenge.components.emails import send_invalid_dockerfile_email
from grandchallenge.components.exceptions import PriorStepFailed
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.uploads.models import UserUpload

logger = logging.getLogger(__name__)

MAX_RETRIES = 60 * 24  # 1 day assuming 60 seconds delay


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def update_sagemaker_shim_version():
    """Updates existing images to new versions of sagemaker shim"""
    with transaction.atomic():
        for app_label, model_name in (
            ("algorithms", "algorithmimage"),
            ("evaluation", "method"),
        ):
            model = apps.get_model(app_label=app_label, model_name=model_name)

            for instance in model.objects.executable_images().exclude(
                latest_shimmed_version=settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
            ):
                on_commit(
                    shim_image.signature(
                        kwargs={
                            "pk": str(instance.pk),
                            "app_label": instance._meta.app_label,
                            "model_name": instance._meta.model_name,
                        }
                    ).apply_async
                )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def shim_image(*, pk: uuid.UUID, app_label: str, model_name: str):
    """Shim an existing container image"""
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if (
        instance.is_manifest_valid
        and instance.is_in_registry
        and instance.SHIM_IMAGE
        and instance.latest_shimmed_version
        != settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
    ):
        shim_container_image(instance=instance)
        instance.is_on_sagemaker = False
        instance.save()

        if settings.COMPONENTS_CREATE_SAGEMAKER_MODEL:
            # Only create SageMaker models for shimmed images for now
            create_sagemaker_model(repo_tag=instance.shimmed_repo_tag)
            instance.is_on_sagemaker = True
            instance.save()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def assign_docker_image_from_upload(
    *, pk: uuid.UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    with transaction.atomic():
        instance.user_upload.copy_object(to_field=instance.image)
        instance.user_upload.delete()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def validate_docker_image(*, pk: uuid.UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    instance.import_status = instance.ImportStatusChoices.STARTED
    instance.save()

    if instance.is_manifest_valid is None:
        try:
            instance.image_sha256 = _validate_docker_image_manifest(
                instance=instance
            )
            instance.is_manifest_valid = True
            instance.save()
        except ValidationError as error:
            instance.image_sha256 = ""
            instance.is_manifest_valid = False
            instance.status = oxford_comma(error)
            instance.import_status = instance.ImportStatusChoices.FAILED
            instance.save()
            send_invalid_dockerfile_email(container_image=instance)
            return
    elif instance.is_manifest_valid is False:
        # Nothing to do
        return

    if not instance.is_in_registry:
        try:
            push_container_image(instance=instance)
            instance.is_in_registry = True
            instance.save()
        except ValidationError as error:
            instance.is_in_registry = False
            instance.status = oxford_comma(error)
            instance.import_status = instance.ImportStatusChoices.FAILED
            instance.save()
            send_invalid_dockerfile_email(container_image=instance)
            return

    if instance.SHIM_IMAGE and (
        instance.latest_shimmed_version
        != settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
    ):
        shim_container_image(instance=instance)
        instance.is_on_sagemaker = False
        instance.save()

    if (
        instance.SHIM_IMAGE
        and settings.COMPONENTS_CREATE_SAGEMAKER_MODEL
        and not instance.is_on_sagemaker
    ):
        # Only create SageMaker models for shimmed images for now
        # See ComponentImageManager
        create_sagemaker_model(repo_tag=instance.shimmed_repo_tag)
        instance.is_on_sagemaker = True
        instance.save()

    instance.import_status = instance.ImportStatusChoices.COMPLETED
    instance.save()


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def remove_inactive_container_images():
    """Removes inactive container images from the registry"""
    for app_label, model_name, related_name in (
        ("algorithms", "algorithm", "algorithm_container_images"),
        ("evaluation", "phase", "method_set"),
        ("workstations", "workstation", "workstationimage_set"),
    ):
        model = apps.get_model(app_label=app_label, model_name=model_name)

        for instance in model.objects.all():
            latest = instance.latest_executable_image

            if latest is not None:
                for image in (
                    getattr(instance, related_name)
                    .exclude(pk=latest.pk)
                    .filter(is_in_registry=True)
                ):
                    on_commit(
                        remove_container_image_from_registry.signature(
                            kwargs={
                                "pk": image.pk,
                                "app_label": image._meta.app_label,
                                "model_name": image._meta.model_name,
                            }
                        ).apply_async
                    )


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def remove_container_image_from_registry(
    *, pk: uuid.UUID, app_label: str, model_name: str
):
    """Remove a container image from the registry"""
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if instance.is_on_sagemaker:
        delete_sagemaker_model(repo_tag=instance.shimmed_repo_tag)
        instance.is_on_sagemaker = False
        instance.save()

    if instance.latest_shimmed_version:
        remove_tag_from_registry(repo_tag=instance.shimmed_repo_tag)
        instance.latest_shimmed_version = ""
        instance.save()

    if instance.is_in_registry:
        remove_tag_from_registry(repo_tag=instance.original_repo_tag)
        instance.is_in_registry = False
        instance.save()


def push_container_image(*, instance):
    if not instance.is_manifest_valid:
        raise RuntimeError("Cannot push invalid instance to registry")

    try:
        with NamedTemporaryFile(suffix=".tar") as o:
            with instance.image.open(mode="rb") as im:
                # Rewrite to tar as crane cannot handle gz
                _decompress_tarball(in_fileobj=im, out_fileobj=o)

            _repo_login_and_run(
                command=["crane", "push", o.name, instance.original_repo_tag]
            )
    except OSError:
        raise ValidationError(
            "The container image is too large, please reduce the size by "
            "optimizing the layers of the container image."
        )


def remove_tag_from_registry(*, repo_tag):
    if settings.COMPONENTS_REGISTRY_INSECURE:
        digest_cmd = _repo_login_and_run(command=["crane", "digest", repo_tag])

        digests = digest_cmd.stdout.decode("utf-8").splitlines()

        for digest in digests:
            _repo_login_and_run(
                command=["crane", "delete", f"{repo_tag}@{digest}"]
            )
    else:
        client = boto3.client(
            "ecr", region_name=settings.COMPONENTS_AMAZON_ECR_REGION
        )

        repo_name, image_tag = repo_tag.rsplit(":", 1)
        repo_name = repo_name.replace(
            f"{settings.COMPONENTS_REGISTRY_URL}/", "", 1
        )

        client.batch_delete_image(
            repositoryName=repo_name,
            imageIds=[
                {"imageTag": image_tag},
            ],
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

    if not instance.is_in_registry:
        raise RuntimeError(
            "The instance must be in the registry to create a SageMaker model"
        )

    # Set the new version, so we can then get the value of the new tag.
    # Do not save the instance until the container image has been mutated.
    instance.latest_shimmed_version = (
        settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
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
        "no_proxy": "amazonaws.com",
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

    architecture = config.get("architecture")
    if architecture != "amd64":
        raise ValidationError(
            f"Architecture type {architecture!r} is not supported. "
            "Please provide a container image built for amd64."
        )

    return f"sha256:{image_sha256}"


def _extract_docker_image_file(*, instance, filename: str):
    """Extract a file from the root of a tarball."""
    try:
        with instance.image.open(mode="rb") as im, tarfile.open(
            fileobj=im, mode="r"
        ) as t:
            member = dict(zip(t.getnames(), t.getmembers(), strict=True))[
                filename
            ]
            file = t.extractfile(member).read()
        return file
    except (KeyError, tarfile.ReadError):
        raise ValidationError(
            f"{filename} not found at the root of the container image "
            f"file. Was this created with docker save?"
        )
    except (EOFError, zlib.error):
        raise ValidationError("Could not decompress the container image file.")


def create_sagemaker_model(*, repo_tag):
    sagemaker_client = boto3.client(
        "sagemaker",
        region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
    )

    sagemaker_client.create_model(
        ModelName=get_sagemaker_model_name(repo_tag=repo_tag),
        PrimaryContainer={"Image": repo_tag},
        ExecutionRoleArn=settings.COMPONENTS_AMAZON_SAGEMAKER_EXECUTION_ROLE_ARN,
        EnableNetworkIsolation=False,  # Restricted by VPC
        VpcConfig={
            "SecurityGroupIds": [
                settings.COMPONENTS_AMAZON_SAGEMAKER_SECURITY_GROUP_ID,
            ],
            "Subnets": settings.COMPONENTS_AMAZON_SAGEMAKER_SUBNETS,
        },
    )


def delete_sagemaker_model(*, repo_tag):
    sagemaker_client = boto3.client(
        "sagemaker",
        region_name=settings.COMPONENTS_AMAZON_ECR_REGION,
    )

    sagemaker_client.delete_model(
        ModelName=get_sagemaker_model_name(repo_tag=repo_tag)
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
def get_model_instance(*, app_label, model_name, **kwargs):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    return model.objects.get(**kwargs)


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


def _delay(*, task, signature_kwargs):
    """Create a task signature for the delay queue"""
    step = task.signature(**signature_kwargs)
    queue = step.options.get("queue", task.queue)
    step.options["queue"] = f"{queue}-delay"
    return step


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
        step = _delay(task=task, signature_kwargs=signature_kwargs)
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
        deprovision_job.signature(**job.signature_kwargs).apply_async()
        raise PriorStepFailed("Job is not set to be executed")

    if not job.container.can_execute:
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

    job_params = Backend.get_job_params(event=event)

    job = get_model_instance(
        pk=job_params.pk,
        app_label=job_params.app_label,
        model_name=job_params.model_name,
        attempt=job_params.attempt,
    )
    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTING:
        deprovision_job.signature(**job.signature_kwargs).apply_async()
        raise PriorStepFailed("Job is not executing")

    try:
        executor.handle_event(event=event)
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
                duration=executor.duration,
                runtime_metrics=executor.runtime_metrics,
                error_message="Time limit exceeded",
            )
            raise
    except RetryTask:
        job.update_status(status=job.PROVISIONED)
        step = _delay(task=retry_task, signature_kwargs=job.signature_kwargs)
        on_commit(step.apply_async)
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            duration=executor.duration,
            runtime_metrics=executor.runtime_metrics,
            error_message=str(e),
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            duration=executor.duration,
            runtime_metrics=executor.runtime_metrics,
            error_message="An unexpected error occurred",
        )
        raise
    else:
        job.update_status(
            status=job.EXECUTED,
            stdout=executor.stdout,
            stderr=executor.stderr,
            duration=executor.duration,
            runtime_metrics=executor.runtime_metrics,
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
        deprovision_job.signature(**job.signature_kwargs).apply_async()
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
def retry_task(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
    retries: int = 0,
):
    """Retries an existing task that was previously provisioned"""
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status != job.PROVISIONED:
        raise PriorStepFailed("Job is not provisioned")

    try:
        executor.deprovision()
    except RetryStep:
        _retry(
            task=retry_task,
            signature_kwargs=job.signature_kwargs,
            retries=retries,
        )

    with transaction.atomic():
        if job.attempt < 99:
            job.status = job.PENDING
            job.attempt += 1
            job.save()

            on_commit(
                provision_job.signature(**job.signature_kwargs).apply_async
            )
        else:
            raise RuntimeError("Maximum attempts exceeded")


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"])
def deprovision_job(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
    retries: int = 0,
):
    job = get_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    try:
        executor.deprovision()
    except RetryStep:
        _retry(
            task=deprovision_job,
            signature_kwargs=job.signature_kwargs,
            retries=retries,
        )


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


@shared_task(
    **settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-micro-short"],
)
def add_image_to_component_interface_value(
    *, component_interface_value_pk, upload_session_pk
):
    with transaction.atomic():
        session = RawImageUploadSession.objects.get(pk=upload_session_pk)

        if session.image_set.count() != 1:
            session.status = RawImageUploadSession.FAILURE
            session.error_message = (
                "Image imports should result in a single image"
            )
            session.save()
            return

        civ = get_model_instance(
            pk=component_interface_value_pk,
            app_label="components",
            model_name="componentinterfacevalue",
        )

        civ.image = session.image_set.get()
        civ.full_clean()
        civ.save()

        civ.image.update_viewer_groups_permissions()


@shared_task
def add_file_to_component_interface_value(
    *,
    component_interface_value_pk,
    user_upload_pk,
    target_pk,
    target_app,
    target_model,
):
    user_upload = UserUpload.objects.get(pk=user_upload_pk)
    civ = get_model_instance(
        pk=component_interface_value_pk,
        app_label="components",
        model_name="componentinterfacevalue",
    )
    target = get_model_instance(
        pk=target_pk,
        app_label=target_app,
        model_name=target_model,
    )
    error = None
    with transaction.atomic():
        try:
            civ.validate_user_upload(user_upload)
            civ.full_clean()
        except ValidationError as e:
            civ.delete()
            error = str(e)
        else:
            user_upload.copy_object(to_field=civ.file)
            civ.save()
            user_upload.delete()

    if error is not None:
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.FILE_COPY_STATUS,
            actor=user_upload.creator,
            message=f"File for interface {civ.interface.title} failed validation.",
            target=target,
            description=(
                f"File for interface {civ.interface.title} failed validation:\n{error}."
            ),
        )


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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def validate_voxel_values(*, civ_pk):
    civ = get_model_instance(
        pk=civ_pk,
        app_label="components",
        model_name="componentinterfacevalue",
    )

    first_file = civ.image.files.first()
    if (
        civ.image.segments is None
        and first_file.image_type == ImageFile.IMAGE_TYPE_MHD
    ):
        sitk_image = SimpleITKImage(
            image=get_sitk_image(image=civ.image),
            name=civ.image.name,
            consumed_files=set(),
            spacing_valid=True,
        )
        segments = sitk_image.segments
        if segments is not None:
            civ.image.segments = [int(segment) for segment in segments]
            civ.image.save()

    civ.interface._validate_voxel_values(civ.image)
