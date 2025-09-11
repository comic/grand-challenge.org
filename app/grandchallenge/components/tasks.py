import gzip
import itertools
import json
import shlex
import subprocess
import tarfile
import uuid
import zlib
from base64 import b64decode, b64encode
from binascii import hexlify
from lzma import LZMAError
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import boto3
from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import (  # noqa: I251 TODO needs to be refactored
    shared_task,
    signature,
)
from celery.utils.log import get_task_logger
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import OperationalError, transaction
from django.db.models import Count, DateTimeField, ExpressionWrapper, F, Q
from django.db.transaction import on_commit
from django.utils.module_loading import import_string
from django.utils.timezone import now
from panimg.models import SimpleITKImage

from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
    ComponentException,
    RetryStep,
    RetryTask,
    TaskCancelled,
)
from grandchallenge.components.emails import send_invalid_dockerfile_email
from grandchallenge.components.exceptions import InstanceInUse, PriorStepFailed
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.core.celery import (
    _retry,
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.utils.error_messages import (
    format_validation_error_message,
)
from grandchallenge.uploads.models import UserUpload

logger = get_task_logger(__name__)


@acks_late_2xlarge_task
@transaction.atomic
def update_all_container_image_shims():
    """Updates existing images to new versions of sagemaker shim"""
    for app_label, model_name in (
        ("algorithms", "algorithmimage"),
        ("evaluation", "method"),
    ):
        model = apps.get_model(app_label=app_label, model_name=model_name)

        for instance in model.objects.executable_images().exclude(
            latest_shimmed_version=settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
        ):
            on_commit(
                update_container_image_shim.signature(
                    kwargs={
                        "pk": str(instance.pk),
                        "app_label": instance._meta.app_label,
                        "model_name": instance._meta.model_name,
                    }
                ).apply_async
            )


@acks_late_2xlarge_task
def assign_docker_image_from_upload(
    *, pk: uuid.UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    with transaction.atomic():
        instance.user_upload.copy_object(to_field=instance.image)
        instance.user_upload.delete()


@acks_late_2xlarge_task
def validate_docker_image(  # noqa C901
    *, pk: uuid.UUID, app_label: str, model_name: str, mark_as_desired: bool
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)
    instance.import_status = instance.ImportStatusChoices.STARTED
    instance.save()

    if instance.is_manifest_valid is None:
        try:
            _validate_docker_image_manifest(instance=instance)
            instance.is_manifest_valid = True
            instance.save()
        except ValidationError as error:
            instance.is_manifest_valid = False
            instance.status = oxford_comma(error)
            instance.import_status = instance.ImportStatusChoices.FAILED
            instance.save()
            send_invalid_dockerfile_email(container_image=instance)
            return
    elif instance.is_manifest_valid is False:
        # Nothing to do
        return

    upload_to_registry_and_sagemaker(
        app_label=app_label,
        model_name=model_name,
        pk=pk,
        mark_as_desired=mark_as_desired,
    )


@acks_late_2xlarge_task
def upload_to_registry_and_sagemaker(
    *, pk: uuid.UUID, app_label: str, model_name: str, mark_as_desired: bool
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    instance.import_status = instance.ImportStatusChoices.STARTED
    instance.save()

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
        instance.save()

    instance.import_status = instance.ImportStatusChoices.COMPLETED
    instance.save()

    if mark_as_desired:
        instance.mark_desired_version()


@acks_late_2xlarge_task
def update_container_image_shim(
    *,
    pk: uuid.UUID,
    app_label: str,
    model_name: str,
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if (
        instance.is_in_registry
        and instance.SHIM_IMAGE
        and (
            instance.latest_shimmed_version
            != settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
        )
    ):
        existing_shimmed_repo_tag = instance.shimmed_repo_tag

        remove_tag_from_registry(repo_tag=existing_shimmed_repo_tag)
        instance.latest_shimmed_version = ""
        instance.save()

        shim_container_image(instance=instance)
        instance.save()


@acks_late_2xlarge_task
def remove_inactive_container_images():
    """Removes inactive container images from the registry"""
    for app_label, model_name, related_name in (
        ("algorithms", "algorithm", "algorithm_container_images"),
        ("evaluation", "phase", "method_set"),
        ("workstations", "workstation", "workstationimage_set"),
    ):
        model = apps.get_model(app_label=app_label, model_name=model_name)

        for instance in model.objects.all():
            queryset = getattr(instance, related_name).filter(
                is_in_registry=True
            )

            if instance.active_image:
                queryset = queryset.exclude(pk=instance.active_image.pk)

            for image in queryset:
                on_commit(
                    remove_container_image_from_registry.signature(
                        kwargs={
                            "pk": image.pk,
                            "app_label": image._meta.app_label,
                            "model_name": image._meta.model_name,
                        }
                    ).apply_async
                )


@acks_late_2xlarge_task
@transaction.atomic
def delete_failed_import_container_images():
    from grandchallenge.algorithms.models import AlgorithmImage
    from grandchallenge.components.models import ComponentImage
    from grandchallenge.evaluation.models import Method
    from grandchallenge.workstations.models import WorkstationImage

    for model in (AlgorithmImage, Method, WorkstationImage):
        for image in model.objects.filter(
            is_removed=False,
            import_status=ComponentImage.ImportStatusChoices.FAILED,
        ).iterator():
            on_commit(
                delete_container_image.signature(
                    kwargs={
                        "pk": image.pk,
                        "app_label": image._meta.app_label,
                        "model_name": image._meta.model_name,
                    }
                ).apply_async
            )


@acks_late_2xlarge_task
@transaction.atomic
def delete_old_unsuccessful_container_images():
    from grandchallenge.algorithms.models import AlgorithmImage, Job
    from grandchallenge.evaluation.models import Evaluation, Method
    from grandchallenge.workstations.models import WorkstationImage

    querysets = [
        WorkstationImage.objects.filter(
            is_removed=False, created__lt=now() - relativedelta(years=1)
        ),
        Method.objects.filter(
            is_removed=False, created__lt=now() - relativedelta(years=1)
        )
        .annotate(
            successful_evaluation_count=Count(
                "evaluation", filter=Q(evaluation__status=Evaluation.SUCCESS)
            )
        )
        .filter(successful_evaluation_count=0),
        AlgorithmImage.objects.filter(
            is_removed=False, created__lt=now() - relativedelta(months=3)
        )
        .annotate(
            successful_job_count=Count(
                "job", filter=Q(job__status=Job.SUCCESS)
            )
        )
        .filter(successful_job_count=0),
    ]

    for queryset in querysets:
        for image in queryset.iterator():
            on_commit(
                delete_container_image.signature(
                    kwargs={
                        "pk": image.pk,
                        "app_label": image._meta.app_label,
                        "model_name": image._meta.model_name,
                    }
                ).apply_async
            )


@acks_late_2xlarge_task(ignore_errors=(InstanceInUse,))
def remove_container_image_from_registry(
    *, pk: uuid.UUID, app_label: str, model_name: str
):
    """Remove a container image from the registry"""
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    from grandchallenge.algorithms.models import AlgorithmImage, Job
    from grandchallenge.evaluation.models import Evaluation, Method
    from grandchallenge.workstations.models import Session, WorkstationImage

    if isinstance(instance, Method):
        instance_in_use = (
            Evaluation.objects.filter(
                method=instance,
            )
            .active()
            .exists()
        )
    elif isinstance(instance, AlgorithmImage):
        instance_in_use = (
            Evaluation.objects.filter(
                submission__algorithm_image=instance,
            )
            .active()
            .exists()
            or Job.objects.filter(
                algorithm_image=instance,
            )
            .active()
            .exists()
        )
    elif isinstance(instance, WorkstationImage):
        instance_in_use = (
            Session.objects.filter(workstation_image=instance)
            .active()
            .exists()
        )
    else:
        raise RuntimeError("Unknown instance type")

    if instance_in_use:
        raise InstanceInUse

    if instance.latest_shimmed_version:
        remove_tag_from_registry(repo_tag=instance.shimmed_repo_tag)
        instance.latest_shimmed_version = ""
        instance.is_desired_version = False
        instance.save()

    if instance.is_in_registry:
        remove_tag_from_registry(repo_tag=instance.original_repo_tag)
        instance.is_in_registry = False
        instance.is_desired_version = False
        instance.save()


@acks_late_2xlarge_task(ignore_errors=(InstanceInUse,))
def delete_container_image(*, pk: uuid.UUID, app_label: str, model_name: str):
    from grandchallenge.algorithms.models import AlgorithmImage, Job
    from grandchallenge.components.models import ComponentImage
    from grandchallenge.evaluation.models import Evaluation, Method
    from grandchallenge.workstations.models import WorkstationImage

    remove_container_image_from_registry(
        pk=pk, app_label=app_label, model_name=model_name
    )

    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    if instance.import_status == ComponentImage.ImportStatusChoices.FAILED:
        should_be_protected = False
    elif isinstance(instance, Method):
        should_be_protected = Evaluation.objects.filter(
            method=instance,
            status=Evaluation.SUCCESS,
        ).exists()
    elif isinstance(instance, AlgorithmImage):
        should_be_protected = Job.objects.filter(
            algorithm_image=instance,
            status=Job.SUCCESS,
        ).exists()
    elif isinstance(instance, WorkstationImage):
        should_be_protected = instance.created > (
            now() - relativedelta(years=1)
        )
    else:
        raise RuntimeError("Unknown instance type")

    if should_be_protected:
        raise InstanceInUse

    if instance.image:
        instance.image.delete(save=False)

    instance.is_removed = True
    instance.is_desired_version = False
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
        raise NotImplementedError
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
        ["/bin/sh", "-c", clean_command],
        check=True,
        capture_output=True,
        text=True,
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
    return json.loads(output.stdout)


def _get_shim_env_vars(*, original_config):
    """Get the environment variables for a shimmed container image"""
    cmd = original_config["config"].get("Cmd")
    entrypoint = original_config["config"].get("Entrypoint")
    user = original_config["config"]["User"]

    return {
        "GRAND_CHALLENGE_COMPONENT_CMD_B64J": encode_b64j(val=cmd),
        "GRAND_CHALLENGE_COMPONENT_ENTRYPOINT_B64J": encode_b64j(
            val=entrypoint
        ),
        "GRAND_CHALLENGE_COMPONENT_USER": user,
    }


def _mutate_container_image(
    *, original_repo_tag, new_repo_tag, version, env_vars
):
    """Add the SageMaker Shim executable to a container image"""
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        new_layer = tmp_path / "sagemaker-shim.tar"

        with tarfile.open(new_layer, "w") as f:

            def _set_root_500_perms(
                tarinfo,
            ):
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.mode = 0o500
                return tarinfo

            f.add(
                name=(
                    f"{settings.COMPONENTS_SAGEMAKER_SHIM_LOCATION}/"
                    f"sagemaker-shim-{version}-Linux-x86_64"
                ),
                arcname="/sagemaker-shim",
                filter=_set_root_500_perms,
            )

            for dir in ["/input", "/output", "/tmp"]:
                # staticx will unpack into /tmp
                tarinfo = tarfile.TarInfo(dir)
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.uid = 0
                tarinfo.gid = 0
                tarinfo.mode = 0o755 if dir == "/input" else 0o777
                f.addfile(tarinfo=tarinfo)

        _repo_login_and_run(
            command=[
                "crane",
                "mutate",
                original_repo_tag,
                # Running as root is required on SageMaker Training
                # due to the permissions of most of the filesystem
                # including /tmp which we need to use
                "--user",
                "0",
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
    with (
        tarfile.open(fileobj=in_fileobj, mode="r") as it,
        tarfile.open(fileobj=out_fileobj, mode="w|") as ot,
    ):
        for member in it.getmembers():
            extracted = it.extractfile(member)
            ot.addfile(member, extracted)


def _validate_docker_image_manifest(*, instance) -> str:
    config_and_sha256 = _get_image_config_and_sha256(instance=instance)

    config = config_and_sha256["config"]
    image_sha256 = config_and_sha256["image_sha256"]

    instance.image_sha256 = f"sha256:{image_sha256}"

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
    _, desired_arch = settings.COMPONENTS_CONTAINER_PLATFORM.split("/")
    if architecture != desired_arch:
        raise ValidationError(
            f"Architecture type {architecture!r} is not supported. "
            "Please provide a container image built for "
            f"{desired_arch!r}."
        )

    if instance._meta.model_name != "method":
        # TODO Methods are currently allowed to be duplicated
        model = apps.get_model(
            app_label=instance._meta.app_label,
            model_name=instance._meta.model_name,
        )
        if (
            model.objects.filter(image_sha256=instance.image_sha256)
            .exclude(pk=instance.pk)
            .exists()
        ):
            raise ValidationError(
                "This container image has already been uploaded. "
                "Please re-activate the existing container image or upload a new version."
            )


def _get_image_config_and_sha256(*, instance):
    try:
        with (
            instance.image.open(mode="rb") as im,
            tarfile.open(fileobj=im, mode="r") as open_tarfile,
        ):
            container_image_files = {
                tarinfo.name: tarinfo
                for tarinfo in open_tarfile.getmembers()
                if tarinfo.isfile()
            }

            image_manifest = _get_image_manifest(
                container_image_files=container_image_files,
                open_tarfile=open_tarfile,
            )

            return _get_image_config_file(
                image_manifest=image_manifest,
                container_image_files=container_image_files,
                open_tarfile=open_tarfile,
            )

    except (
        EOFError,
        zlib.error,
        gzip.BadGzipFile,
        LZMAError,
        tarfile.ReadError,
        MemoryError,
    ):
        raise ValidationError("Could not decompress the container image file.")


def _get_image_manifest(*, container_image_files, open_tarfile):
    try:
        manifest = json.loads(
            open_tarfile.extractfile(
                container_image_files["manifest.json"]
            ).read()
        )
    except KeyError:
        raise ValidationError(
            "Could not find manifest.json in the container image file. "
            "Was this created with docker save?"
        )

    if len(manifest) != 1:
        raise ValidationError(
            f"The container image file should only have 1 image. "
            f"This file contains {len(manifest)}."
        )

    return manifest[0]


def _get_image_config_file(
    *, image_manifest, container_image_files, open_tarfile
):
    config_filename = image_manifest["Config"]

    try:
        config = json.loads(
            open_tarfile.extractfile(
                container_image_files[config_filename]
            ).read()
        )
    except KeyError:
        raise ValidationError(
            "Could not find the config file in the container image file. "
            "Was this created with docker save?"
        )

    if config_filename.endswith(".json"):
        # Docker <25 container image
        image_sha256 = config_filename.split(".")[0]
    else:
        # Docker >=25 container image
        image_sha256 = image_manifest["Config"].split("/")[-1]

    if image_sha256.startswith("sha256:"):
        # Images created by crane have a sha256 prefix
        image_sha256 = image_sha256[7:]

    if len(image_sha256) != 64:
        raise ValidationError(
            "The container image file does not have a valid sha256 hash."
        )

    return {"image_sha256": image_sha256, "config": config}


def lock_model_instance(
    *, app_label, model_name, of=(), select_related=(), **kwargs
):
    """
    Locks a model instance for update.

    This is useful when you want to update a model instance and want to make
    sure that no other process is updating the same instance at the same time.
    Must be used inside a transaction.

    Raises `LockNotAcquiredException` if the lock could not be acquired.
    """
    model = apps.get_model(app_label=app_label, model_name=model_name)

    queryset = model.objects.filter(**kwargs)

    if select_related:
        queryset = queryset.select_related(*select_related)

    queryset = queryset.select_for_update(of=of, nowait=True)

    try:
        return queryset.get()
    except OperationalError as error:
        check_operational_error(error)
        raise


def check_operational_error(error):
    if "could not obtain lock" in str(error):
        raise LockNotAcquiredException from error
    else:
        raise error


def lock_for_utilization_update(*, algorithm_image_pk):
    from grandchallenge.algorithms.models import AlgorithmImage

    # Lock the algorithm and algorithm image to avoid conflicts
    # when modifying JobUtilization objects
    try:
        AlgorithmImage.objects.filter(pk=algorithm_image_pk).select_related(
            "algorithm"
        ).select_for_update(
            of=("self", "algorithm"),
            nowait=True,
            no_key=True,
        ).get()
    except OperationalError as error:
        check_operational_error(error)
        raise


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def provision_job(
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str, backend: str
):
    job = lock_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if not job.inputs_complete or job.status not in [job.PENDING, job.RETRY]:
        raise RuntimeError("Job is not ready for provisioning")

    try:
        executor.provision(
            input_civs=job.inputs.prefetch_related(
                "interface", "image__files"
            ).all(),
            input_prefixes=job.input_prefixes,
        )
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            error_message=str(e),
            detailed_error_message=e.message_details,
        )
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="An unexpected error occurred"
        )
        logger.error("Could not provision job", exc_info=True)
    else:
        job.update_status(status=job.PROVISIONED)
        on_commit(execute_job.signature(**job.signature_kwargs).apply_async)


@acks_late_micro_short_task(retry_on=(RetryStep,))
def execute_job(  # noqa: C901
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
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)
    job = model.objects.get(pk=job_pk)
    executor = job.get_executor(backend=backend)

    if job.status == job.PROVISIONED:
        job.update_status(status=job.EXECUTING)
    else:
        deprovision_job.signature(**job.signature_kwargs).apply_async()
        raise PriorStepFailed("Job is not set to be executed")

    if not job.container.can_execute:
        # TODO matching on this error message is used, perhaps it should be cancelled instead, see #4119
        msg = f"Container Image {job.container.pk} was not ready to be used"
        job.update_status(status=job.FAILURE, error_message=msg)
        raise PriorStepFailed(msg)

    try:
        executor.execute()
    except RetryStep:
        job.update_status(status=job.PROVISIONED)
        raise
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message=str(e),
            detailed_error_message=e.message_details,
        )
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message="Time limit exceeded",
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            stdout=executor.stdout,
            stderr=executor.stderr,
            error_message="An unexpected error occurred",
        )
        raise


def get_update_status_kwargs(*, executor=None):
    if executor is not None:
        return {
            "stdout": executor.stdout,
            "stderr": executor.stderr,
            "duration": executor.duration,
            "compute_cost_euro_millicents": executor.compute_cost_euro_millicents,
            "runtime_metrics": executor.runtime_metrics,
        }
    else:
        return {}


@acks_late_micro_short_task(retry_on=(RetryStep, LockNotAcquiredException))
@transaction.atomic
def handle_event(*, event, backend):  # noqa: C901
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

    job_name = Backend.get_job_name(event=event)
    job_params = Backend.get_job_params(job_name=job_name)

    job = lock_model_instance(
        pk=job_params.pk,
        attempt=job_params.attempt,
        app_label=job_params.app_label,
        model_name=job_params.model_name,
        of=("self",),
    )

    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTING:
        # Nothing to do
        return

    if hasattr(job, "algorithm_image"):
        lock_for_utilization_update(algorithm_image_pk=job.algorithm_image_id)

    try:
        executor.handle_event(event=event)
    except TaskCancelled:
        job.update_status(
            status=job.CANCELLED, **get_update_status_kwargs(executor=executor)
        )
        return
    except RetryStep:
        raise
    except RetryTask:
        job.update_status(status=job.PROVISIONED)
        _retry(
            task=retry_task, signature_kwargs=job.signature_kwargs, retries=0
        )
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            error_message=str(e),
            detailed_error_message=e.message_details,
            **get_update_status_kwargs(executor=executor),
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            error_message="An unexpected error occurred",
            **get_update_status_kwargs(executor=executor),
        )
        raise
    else:
        job.update_status(
            status=job.EXECUTED,
            **get_update_status_kwargs(executor=executor),
        )
        on_commit(
            parse_job_outputs.signature(**job.signature_kwargs).apply_async
        )


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def parse_job_outputs(
    *, job_pk: uuid.UUID, job_app_label: str, job_model_name: str, backend: str
):
    job = lock_model_instance(
        pk=job_pk, app_label=job_app_label, model_name=job_model_name
    )
    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTED:
        raise RuntimeError("Job is not ready for output parsing")

    if job.outputs.exists():
        raise RuntimeError("Job already has outputs")

    try:
        outputs = executor.get_outputs(
            output_interfaces=job.output_interfaces.all()
        )
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            error_message=str(e),
            detailed_error_message=e.message_details,
        )
    except Exception:
        job.update_status(
            status=job.FAILURE, error_message="An unexpected error occurred"
        )
        logger.error("Could not parse outputs", exc_info=True)
    else:
        job.outputs.add(*outputs)
        job.update_status(status=job.SUCCESS)


@acks_late_micro_short_task(retry_on=(RetryStep,))
def retry_task(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    """Retries an existing task that was previously provisioned"""
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)
    job = model.objects.get(pk=job_pk)
    executor = job.get_executor(backend=backend)

    if job.status != job.PROVISIONED:
        raise PriorStepFailed("Job is not provisioned")

    executor.deprovision()

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


@acks_late_micro_short_task(retry_on=(RetryStep,))
def deprovision_job(
    *,
    job_pk: uuid.UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)
    job = model.objects.get(pk=job_pk)

    executor = job.get_executor(backend=backend)
    executor.deprovision()


@shared_task
def start_service(*, pk: uuid.UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    session = model.objects.get(pk=pk)
    session.start()


@shared_task
def stop_service(*, pk: uuid.UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    session = model.objects.get(pk=pk)
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


class InteractiveAlgorithm:
    def __init__(self, *, region_name, arn, qualifier, should_be_active):
        self._region_name = region_name
        self._arn = arn
        self._qualifier = str(qualifier)
        self._should_be_active = bool(should_be_active)

        self._lambda_client = None

    @property
    def lambda_client(self):
        if self._lambda_client is None:
            self._lambda_client = boto3.client(
                "lambda", region_name=self._region_name
            )
        return self._lambda_client

    def consolidate(self):
        active_status = self.set_active_provisioned_concurrency_config()
        deleted = self.delete_stale_provisioned_concurrency_configs()
        return {"active_status": active_status, "deleted": deleted}

    @property
    def provisioned_concurrency_qualifiers(self):
        provisioned_concurrency_qualifiers = set()

        paginator = self.lambda_client.get_paginator(
            "list_provisioned_concurrency_configs"
        )

        for page in paginator.paginate(FunctionName=self._arn):
            for config in page.get("ProvisionedConcurrencyConfigs", []):
                qualifier = config["FunctionArn"].rsplit(":", 1)[-1]
                provisioned_concurrency_qualifiers.add(qualifier)

        return provisioned_concurrency_qualifiers

    def set_active_provisioned_concurrency_config(self):
        if self._should_be_active:
            invoked = False

            try:
                config = self.lambda_client.get_provisioned_concurrency_config(
                    FunctionName=self._arn,
                    Qualifier=self._qualifier,
                )
            except (
                self.lambda_client.exceptions.ProvisionedConcurrencyConfigNotFoundException
            ):
                config = self.lambda_client.put_provisioned_concurrency_config(
                    FunctionName=self._arn,
                    ProvisionedConcurrentExecutions=1,
                    Qualifier=self._qualifier,
                )
                self.lambda_client.invoke(
                    FunctionName=self._arn,
                    InvocationType="Event",
                    Payload=json.dumps({}),
                    Qualifier=self._qualifier,
                )
                invoked = True

            return {
                "qualifier": self._qualifier,
                "status": config["Status"],
                "invoked": invoked,
            }
        else:
            return {}

    def delete_stale_provisioned_concurrency_configs(self):
        deleted = []

        for qualifier in self.provisioned_concurrency_qualifiers:
            if qualifier != self._qualifier or self._should_be_active is False:
                self.lambda_client.delete_provisioned_concurrency_config(
                    FunctionName=self._arn,
                    Qualifier=qualifier,
                )
                deleted.append(qualifier)

        return deleted


@shared_task
@transaction.atomic
def preload_interactive_algorithms():
    from grandchallenge.reader_studies.models import Question
    from grandchallenge.workstations.models import Session

    region_name = settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS[
        "region_name"
    ]

    active_interactive_algorithms = (
        Question.objects.filter(
            reader_study__workstation_sessions__status__in=[
                Session.QUEUED,
                Session.STARTED,
                Session.RUNNING,
            ],
            reader_study__workstation_sessions__region=region_name,
        )
        .exclude(interactive_algorithm="")
        .values_list("interactive_algorithm", flat=True)
        .distinct()
    )

    consolidation_results = {}

    for lamba_function in settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS[
        "lambda_functions"
    ]:
        interactive_algorithm = InteractiveAlgorithm(
            region_name=region_name,
            arn=lamba_function["arn"],
            qualifier=lamba_function["version"],
            should_be_active=lamba_function["internal_name"]
            in active_interactive_algorithms,
        )
        consolidation_results[lamba_function["internal_name"]] = (
            interactive_algorithm.consolidate()
        )

    return consolidation_results


@acks_late_2xlarge_task
@transaction.atomic
def civ_value_to_file(*, civ_pk):
    from grandchallenge.components.models import ComponentInterfaceValue

    civ = ComponentInterfaceValue.objects.get(pk=civ_pk)

    if civ.value is None:
        raise RuntimeError("CIV value is None")

    civ.file = ContentFile(
        json.dumps(civ.value).encode("utf-8"),
        name=Path(civ.interface.relative_path).name,
    )
    civ.value = None
    civ.save()


@acks_late_2xlarge_task
def validate_voxel_values(*, civ_pk):
    from grandchallenge.components.models import ComponentInterfaceValue

    civ = ComponentInterfaceValue.objects.get(pk=civ_pk)

    first_file = civ.image.files.first()
    if (
        civ.image.segments is None
        and first_file.image_type == ImageFile.IMAGE_TYPE_MHD
    ):
        sitk_image = SimpleITKImage(
            image=civ.image.sitk_image,
            name=civ.image.name,
            consumed_files=set(),
            spacing_valid=True,
        )
        segments = sitk_image.segments
        if segments is not None:
            civ.image.segments = [int(segment) for segment in segments]
            civ.image.save()

    civ.interface._validate_voxel_values(civ.image)


@acks_late_micro_short_task(
    retry_on=(LockNotAcquiredException,), delayed_retry=False
)
@transaction.atomic
def add_image_to_object(  # noqa: C901
    *,
    app_label,
    model_name,
    object_pk,
    interface_pk,
    upload_session_pk,
    linked_task=None,
):
    from grandchallenge.algorithms.models import Job
    from grandchallenge.archives.models import ArchiveItem
    from grandchallenge.components.models import (
        ComponentInterface,
        ComponentInterfaceValue,
    )
    from grandchallenge.reader_studies.models import DisplaySet

    try:
        object = lock_model_instance(
            app_label=app_label, model_name=model_name, pk=object_pk
        )
    except (ArchiveItem.DoesNotExist, DisplaySet.DoesNotExist):
        logger.info(f"Nothing to do: {model_name} no longer exists.")
        return

    interface = ComponentInterface.objects.get(pk=interface_pk)
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_pk)

    if upload_session.status != upload_session.SUCCESS:
        logger.info("Nothing to do: upload session was not successful.")
        return

    error_handler = object.get_error_handler(linked_object=upload_session)

    try:
        image = Image.objects.get(origin_id=upload_session_pk)
    except (Image.DoesNotExist, Image.MultipleObjectsReturned):
        error_handler.handle_error(
            interface=interface,
            error_message="Image imports should result in a single image",
            user=upload_session.creator,
        )
        logger.info("Upload session should only have one image")
        return

    current_value = object.get_current_value_for_interface(
        interface=interface, user=upload_session.creator
    )

    civ, created = ComponentInterfaceValue.objects.get_first_or_create(
        interface=interface, image=image
    )

    if created:
        try:
            civ.full_clean()
        except ValidationError as e:
            error_handler.handle_error(
                interface=interface,
                error_message=format_validation_error_message(error=e),
                user=upload_session.creator,
            )
            logger.info(f"Validation failed: {e}")
            return
        except Exception as e:
            error_handler.handle_error(
                interface=interface,
                error_message="An unexpected error occurred",
                user=upload_session.creator,
            )
            logger.error(e, exc_info=True)
            return

    try:
        object.remove_civ(civ=current_value)
        object.add_civ(civ=civ)
    except CIVNotEditableException as e:
        if isinstance(object, Job) and object.status == Job.CANCELLED:
            logger.info("Job has been cancelled, exiting")
            return
        else:
            error_handler.handle_error(
                interface=interface,
                error_message="An unexpected error occurred",
                user=upload_session.creator,
            )
            logger.error(e, exc_info=True)
            return

    if linked_task is not None:
        logger.info("Scheduling linked task")
        on_commit(signature(linked_task).apply_async)
    else:
        logger.info("No linked task, task complete")


@acks_late_micro_short_task(
    retry_on=(LockNotAcquiredException,), delayed_retry=False
)
@transaction.atomic
def add_file_to_object(
    *,
    app_label,
    model_name,
    user_upload_pk,
    object_pk,
    interface_pk,
    linked_task=None,
):
    from grandchallenge.algorithms.models import Job
    from grandchallenge.archives.models import ArchiveItem
    from grandchallenge.components.models import (
        ComponentInterface,
        ComponentInterfaceValue,
    )
    from grandchallenge.reader_studies.models import DisplaySet

    try:
        object = lock_model_instance(
            app_label=app_label, model_name=model_name, pk=object_pk
        )
    except (ArchiveItem.DoesNotExist, DisplaySet.DoesNotExist):
        logger.info(f"Nothing to do: {model_name} no longer exists.")
        return

    interface = ComponentInterface.objects.get(pk=interface_pk)
    user_upload = UserUpload.objects.get(pk=user_upload_pk)
    error_handler = object.get_error_handler(linked_object=user_upload)

    current_value = object.get_current_value_for_interface(
        interface=interface, user=user_upload.creator
    )

    civ = ComponentInterfaceValue(interface=interface)
    try:
        civ.validate_user_upload(user_upload)
        civ.full_clean()
        civ.save()
        user_upload.copy_object(to_field=civ.file)
        user_upload.delete()
    except ValidationError as e:
        error_handler.handle_error(
            interface=interface,
            error_message=format_validation_error_message(e),
            user=user_upload.creator,
        )
        logger.info(f"Validation failed: {e}")
        return
    except Exception as e:
        error_handler.handle_error(
            interface=interface,
            error_message="An unexpected error occurred",
            user=user_upload.creator,
        )
        logger.error(e, exc_info=True)
        return

    try:
        object.remove_civ(civ=current_value)
        object.add_civ(civ=civ)
    except CIVNotEditableException as e:
        if isinstance(object, Job) and object.status == Job.CANCELLED:
            logger.info("Job has been cancelled, exiting")
            return
        else:
            error_handler.handle_error(
                interface=interface,
                error_message="An unexpected error occurred",
                user=user_upload.creator,
            )
            logger.error(e, exc_info=True)
            return

    if linked_task is not None:
        logger.info("Scheduling linked task")
        on_commit(signature(linked_task).apply_async)
    else:
        logger.info("No linked task, task complete")


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def assign_tarball_from_upload(
    *, app_label, model_name, tarball_pk, field_to_copy
):
    from grandchallenge.components.models import ImportStatusChoices

    TarballModel = apps.get_model(  # noqa: N806
        app_label=app_label, model_name=model_name
    )

    current_tarball = lock_model_instance(
        pk=tarball_pk,
        import_status=ImportStatusChoices.INITIALIZED,
        app_label=app_label,
        model_name=model_name,
    )

    try:
        # Acquire locks
        peer_tarballs = list(
            current_tarball.get_peer_tarballs().select_for_update(nowait=True)
        )
    except OperationalError as error:
        check_operational_error(error)
        raise

    current_tarball.user_upload.copy_object(
        to_field=getattr(current_tarball, field_to_copy)
    )

    sha256 = get_object_sha256(getattr(current_tarball, field_to_copy))
    if (
        TarballModel.objects.filter(sha256=sha256)
        .exclude(pk=current_tarball.pk)
        .exists()
    ):
        current_tarball.import_status = ImportStatusChoices.FAILED
        current_tarball.status = f"{TarballModel._meta.verbose_name} with this sha256 already exists."
        current_tarball.save()

        getattr(current_tarball, field_to_copy).delete()
        current_tarball.user_upload.delete()

        return

    current_tarball.sha256 = sha256
    current_tarball.size_in_storage = getattr(
        current_tarball, field_to_copy
    ).size
    current_tarball.import_status = ImportStatusChoices.COMPLETED
    current_tarball.save()

    current_tarball.user_upload.delete()

    # mark as desired version and pass locked peer tarballs directly since else
    # mark_desired_version will fail trying to access the locked tarballs
    current_tarball.mark_desired_version(peer_tarballs=peer_tarballs)


def get_object_sha256(file_field):
    response = file_field.storage.connection.meta.client.head_object(
        Bucket=file_field.storage.bucket.name,
        Key=file_field.name,
        ChecksumMode="ENABLED",
    )

    # The checksums are not calculated on minio
    if sha256 := response.get("ChecksumSHA256"):
        return f"sha256:{hexlify(b64decode(sha256)).decode('utf-8')}"
    else:
        return ""
