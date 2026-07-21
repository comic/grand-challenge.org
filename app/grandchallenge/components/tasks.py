import gzip
import itertools
import json
import shlex
import subprocess
import tarfile
import zlib
from base64 import b64decode, b64encode
from binascii import hexlify
from lzma import LZMAError
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import UUID

import boto3
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Count, DateTimeField, ExpressionWrapper, F, Q
from django.utils.module_loading import import_string
from django.utils.timezone import now
from lambda_tasks.decorators import lambda_task
from lambda_tasks.logging import task_logger
from lambda_tasks.models import SQSLambdaTask
from lambda_tasks.settings import MAX_DELAY
from lambda_tasks.timeouts import SoftTimeLimitExceeded

from config.lambda_tasks import (
    BATCH_LONG_TASK_HARD_TIMEOUT,
    BATCH_LONG_TASK_SOFT_TIMEOUT,
    LONG_TASK_HARD_TIMEOUT,
    LONG_TASK_SOFT_TIMEOUT,
    LambdaTaskQueueChoices,
)
from grandchallenge.cases.models import (
    DICOMImageSetUpload,
    DICOMImageSetUploadStatusChoices,
    Image,
    RawImageUploadSession,
)
from grandchallenge.components.backends.amazon_ecs import ECSTaskOrchestrator
from grandchallenge.components.backends.exceptions import (
    CIVNotEditableException,
    ComponentException,
    RetryStep,
    RetryTask,
    TaskCancelled,
)
from grandchallenge.components.emails import (
    send_container_image_not_made_active,
    send_invalid_dockerfile_email,
)
from grandchallenge.components.exceptions import PriorStepFailed
from grandchallenge.components.registry import _get_registry_auth_config
from grandchallenge.core.error_messages import SystemErrorMessages
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.templatetags.remove_whitespace import oxford_comma
from grandchallenge.core.utils.error_messages import (
    format_validation_error_message,
)
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.uploads.models import UserUpload


@lambda_task
def update_all_container_image_shims():
    """Updates existing images to new versions of sagemaker shim"""
    n_tasks = 0

    for app_label, model_name in (
        ("algorithms", "algorithmimage"),
        ("evaluation", "method"),
    ):
        model = apps.get_model(app_label=app_label, model_name=model_name)

        for instance in model.objects.executable_images().exclude(
            latest_shimmed_version=settings.COMPONENTS_SAGEMAKER_SHIM_VERSION
        ):
            update_container_image_shim.execute_on_commit(
                pk=instance.pk,
                app_label=instance._meta.app_label,
                model_name=instance._meta.model_name,
                _delay=n_tasks % MAX_DELAY,
            )
            n_tasks += 1

    return n_tasks


@lambda_task(queue=LambdaTaskQueueChoices.MEM8G)
def assign_docker_image_from_upload(
    *, pk: str | UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)
    instance = model.objects.get(pk=pk)

    instance.user_upload.copy_object(to_field=instance.image)
    instance.user_upload.delete()


@lambda_task(
    queue=LambdaTaskQueueChoices.BATCH_MEM8G,
    retry_on=(LockNotAcquiredException,),
    soft_timeout=BATCH_LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=BATCH_LONG_TASK_HARD_TIMEOUT,
)
def validate_container_image(
    *,
    pk: str | UUID,
    app_label: str,
    model_name: str,
    mark_as_desired: bool,
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        instance = model.objects.select_for_update(nowait=True).get(pk=pk)

    if instance.import_status != instance.ImportStatusChoices.STARTED:
        raise RuntimeError("Container Image is not ready for validation")

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

    upload_to_registry_and_sagemaker.execute_on_commit(
        app_label=app_label,
        model_name=model_name,
        pk=pk,
        mark_as_desired=mark_as_desired,
    )


@lambda_task(
    queue=LambdaTaskQueueChoices.BATCH_MEM8G,
    retry_on=(LockNotAcquiredException,),
    soft_timeout=BATCH_LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=BATCH_LONG_TASK_HARD_TIMEOUT,
)
def upload_to_registry_and_sagemaker(
    *, pk: str | UUID, app_label: str, model_name: str, mark_as_desired: bool
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        instance = model.objects.select_for_update(nowait=True).get(pk=pk)

    if instance.import_status != instance.ImportStatusChoices.STARTED:
        raise RuntimeError("Container Image is not ready for validation")

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

    if mark_as_desired:
        mark_desired_container_version.execute_on_commit(
            app_label=app_label,
            model_name=model_name,
            pk=pk,
        )
    else:
        instance.import_status = instance.ImportStatusChoices.COMPLETED
        instance.save()


@lambda_task(retry_on=(LockNotAcquiredException,))
def mark_desired_container_version(
    *, pk: str | UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        instance = model.objects.select_for_update(nowait=True).get(pk=pk)

        # Acquire a lock on the peer images
        _ = list(
            instance.get_peer_images()
            .select_for_update(nowait=True)
            .values_list("pk", flat=True)
        )

    if instance.import_status != instance.ImportStatusChoices.STARTED:
        raise RuntimeError("Container Image is not ready for validation")

    instance.import_status = instance.ImportStatusChoices.COMPLETED
    instance.save()

    try:
        instance.mark_desired_version()
    except ValidationError as error:
        send_container_image_not_made_active(
            container_image=instance, error_message=str(error)
        )


@lambda_task(retry_on=(LockNotAcquiredException,))
def update_container_image_shim(
    *,
    pk: str | UUID,
    app_label: str,
    model_name: str,
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        instance = model.objects.select_for_update(
            nowait=True, of=("self",)
        ).get(pk=pk)

    from grandchallenge.algorithms.models import AlgorithmImage, Job
    from grandchallenge.evaluation.models import Evaluation, Method

    if isinstance(instance, AlgorithmImage):
        if Job.objects.active().filter(algorithm_image=instance).exists():
            task_logger.info("Skipping - Algorithm image has an active job")
            return instance.latest_shimmed_version
    elif isinstance(instance, Method):
        if Evaluation.objects.active().filter(method=instance).exists():
            task_logger.info("Skipping - Method has an active evaluation")
            return instance.latest_shimmed_version
    else:
        raise NotImplementedError

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

    return instance.latest_shimmed_version


@lambda_task
def remove_inactive_container_images():
    """Removes inactive container images from the registry"""
    for app_label, model_name, related_name in (
        ("algorithms", "algorithm", "algorithm_container_images"),
        ("evaluation", "phase", "method_set"),
        ("workstations", "workstation", "workstationimage_set"),
    ):
        model = apps.get_model(app_label=app_label, model_name=model_name)

        for instance in model.objects.iterator(chunk_size=1000):
            queryset = getattr(instance, related_name).filter(
                is_in_registry=True
            )

            if instance.active_image:
                queryset = queryset.exclude(pk=instance.active_image.pk)

            for image in queryset:
                remove_container_image_from_registry.execute_on_commit(
                    pk=image.pk,
                    app_label=image._meta.app_label,
                    model_name=image._meta.model_name,
                )


@lambda_task
def delete_failed_import_container_images():
    from grandchallenge.algorithms.models import AlgorithmImage
    from grandchallenge.components.models import ComponentImage
    from grandchallenge.evaluation.models import Method
    from grandchallenge.workstations.models import WorkstationImage

    for model in (AlgorithmImage, Method, WorkstationImage):
        for image in model.objects.filter(
            is_removed=False,
            import_status=ComponentImage.ImportStatusChoices.FAILED,
        ).iterator(chunk_size=1000):
            delete_container_image.execute_on_commit(
                pk=image.pk,
                app_label=image._meta.app_label,
                model_name=image._meta.model_name,
            )


@lambda_task
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
        for image in queryset.iterator(chunk_size=1000):
            delete_container_image.execute_on_commit(
                pk=image.pk,
                app_label=image._meta.app_label,
                model_name=image._meta.model_name,
            )


@lambda_task
def remove_container_image_from_registry(
    *, pk: str | UUID, app_label: str, model_name: str
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
        # Nothing to do
        return

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


@lambda_task
def delete_container_image(*, pk: str | UUID, app_label: str, model_name: str):
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
        # Nothing to do
        return

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

    instance.api_method = _get_image_api_method(config=config)

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


def _get_image_api_method(*, config):
    from grandchallenge.components.models import APIMethodChoices

    label = "org.grand-challenge.api-method"
    allowed_values = APIMethodChoices.values

    labels = config["config"].get("Labels") or {}

    for key, value in labels.items():
        if str(key).lower().strip() == label:
            cleaned_value = (
                str(value).lower().replace("'", "").replace('"', "").strip()
            )
            if cleaned_value in allowed_values:
                return cleaned_value
            else:
                raise ValidationError(
                    f"The label {label} must be one of {allowed_values}, instead we found '{value}'."
                )
    else:
        return APIMethodChoices.EXEC


def lock_for_utilization_update(*, algorithm_image_pk, invoice_pk):
    from grandchallenge.algorithms.models import AlgorithmImage
    from grandchallenge.invoices.models import Invoice

    # Lock the algorithm, algorithm image and invoice to avoid conflicts
    # when modifying JobUtilization objects
    with check_lock_acquired():
        if algorithm_image_pk:
            AlgorithmImage.objects.select_related(
                "algorithm"
            ).select_for_update(
                nowait=True,
                no_key=True,
            ).get(
                pk=algorithm_image_pk
            )

        if invoice_pk:
            Invoice.objects.select_for_update(
                nowait=True,
                no_key=True,
            ).get(pk=invoice_pk)


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G,
    retry_on=(LockNotAcquiredException,),
    soft_timeout=LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=LONG_TASK_HARD_TIMEOUT,
)
def provision_job(
    *,
    job_pk: str | UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)

    with check_lock_acquired():
        job = model.objects.select_for_update(nowait=True).get(pk=job_pk)

    executor = job.get_executor(backend=backend)

    if not job.inputs_complete or job.status not in [job.PENDING, job.RETRY]:
        if job.status == job.CANCELLED:
            # Nothing to do
            return
        else:
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
            status=job.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error("Could not provision job", exc_info=True)
    else:
        job.update_status(status=job.PROVISIONED)
        execute_job.execute_on_commit(**job.task_kwargs)


@lambda_task(retry_on=(RetryStep,), retry_delay=120)
def execute_job(
    *,
    job_pk: str | UUID,
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
        deprovision_job.execute_on_commit(**job.task_kwargs)
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
            error_message=str(e),
            detailed_error_message=e.message_details,
        )
    except SoftTimeLimitExceeded:
        job.update_status(
            status=job.FAILURE,
            error_message=SystemErrorMessages.TIME_LIMIT_EXCEEDED,
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        raise


def get_update_status_kwargs(*, executor=None):
    if executor is not None:
        return {
            "utilization_duration": executor.utilization_duration,
            "exec_duration": executor.exec_duration,
            "invoke_duration": executor.invoke_duration,
            "compute_cost_euro_millicents": executor.compute_cost_euro_millicents,
        }
    else:
        return {}


@lambda_task(retry_on=(RetryStep, LockNotAcquiredException))
def handle_event(*, event: dict, backend: str):
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

    model = apps.get_model(
        app_label=job_params.app_label,
        model_name=job_params.model_name,
    )

    with check_lock_acquired():
        job = model.objects.select_for_update(nowait=True).get(
            pk=job_params.pk, attempt=job_params.attempt
        )

    executor = job.get_executor(backend=backend)

    if job.status != job.EXECUTING:
        # Nothing to do
        return

    if hasattr(job, "algorithm_image"):
        algorithm_image_pk = job.algorithm_image_id
    else:
        algorithm_image_pk = None

    lock_for_utilization_update(
        algorithm_image_pk=algorithm_image_pk,
        invoice_pk=job.utilization.invoice_id,
    )

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
        retry_task.execute_on_commit(**job.task_kwargs)
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            error_message=str(e),
            detailed_error_message=e.message_details,
            **get_update_status_kwargs(executor=executor),
        )
    except Exception as error:
        job.update_status(
            status=job.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
            **get_update_status_kwargs(executor=executor),
        )
        task_logger.error(str(error), exc_info=True)
    else:
        job.update_status(
            status=job.EXECUTED,
            **get_update_status_kwargs(executor=executor),
        )
        parse_job_outputs.execute_on_commit(**job.task_kwargs)


@lambda_task(retry_on=(LockNotAcquiredException,))
def parse_job_outputs(
    *,
    job_pk: str | UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)

    with check_lock_acquired():
        job = model.objects.select_for_update(nowait=True).get(pk=job_pk)

    if job.status != job.EXECUTED:
        raise RuntimeError("Job is not ready for output parsing")

    if job.outputs.exists():
        raise RuntimeError("Job already has outputs")

    interface_pks = list(
        job.output_interfaces.order_by("pk").values_list("pk", flat=True)
    )

    if not interface_pks:
        job.update_status(status=job.SUCCESS)
    else:
        job.update_status(status=job.PARSING)

        # Kick off the parsing chain
        parse_singular_job_output.execute_on_commit(
            job_pk=job_pk,
            job_app_label=job_app_label,
            job_model_name=job_model_name,
            backend=backend,
            interface_pks=interface_pks,
        )


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G, retry_on=(LockNotAcquiredException,)
)
def parse_singular_job_output(
    *,
    job_pk: str | UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
    interface_pks: list[int],
):
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)

    with check_lock_acquired():
        job = model.objects.select_for_update(nowait=True).get(pk=job_pk)

    if job.status != job.PARSING:
        # Check for changes in status
        raise RuntimeError("Job is not in parsing state")

    executor = job.get_executor(backend=backend)

    interface_pk = interface_pks.pop(0)

    interface_model = job.output_interfaces.model
    try:
        interface = interface_model.objects.get(pk=interface_pk)
    except interface_model.DoesNotExist:
        job.update_status(
            status=job.FAILURE,
            error_message=f"Output interface with pk={interface_pk} does not exist",
        )
        return

    try:
        outputs = executor.get_outputs(output_interfaces=[interface])
    except ComponentException as e:
        job.update_status(
            status=job.FAILURE,
            error_message=str(e),
            detailed_error_message=e.message_details,
        )
    except Exception:
        job.update_status(
            status=job.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error("Could not parse outputs", exc_info=True)
    else:
        job.outputs.add(*outputs)
        if interface_pks:
            parse_singular_job_output.execute_on_commit(
                job_pk=job_pk,
                job_app_label=job_app_label,
                job_model_name=job_model_name,
                backend=backend,
                interface_pks=interface_pks,
            )
        else:
            job.update_status(status=job.SUCCESS)


@lambda_task(retry_on=(RetryStep,))
def retry_task(
    *,
    job_pk: str | UUID,
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

    if job.attempt < 99:
        job.status = job.PENDING
        job.attempt += 1
        job.save()

        provision_job.execute_on_commit(**job.task_kwargs)
    else:
        job.update_status(
            status=job.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error("Maximum attempts exceeded")


@lambda_task(retry_on=(RetryStep,))
def deprovision_job(
    *,
    job_pk: str | UUID,
    job_app_label: str,
    job_model_name: str,
    backend: str,
):
    model = apps.get_model(app_label=job_app_label, model_name=job_model_name)
    job = model.objects.get(pk=job_pk)

    executor = job.get_executor(backend=backend)
    executor.deprovision()


@lambda_task(
    retry_on=(
        LockNotAcquiredException,
        RetryStep,
    )
)
def start_service(*, pk: str | UUID, app_label: str, model_name: str):
    """
    Starts the service on ECS.

    Takes jobs in the service.QUEUED state, starts them on ECS,
    then places them in the service.STARTED state.
    """
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        service = model.objects.select_for_update(nowait=True).get(pk=pk)

    if service.status != service.QUEUED:
        raise RuntimeError("Service is not ready for starting")

    if not service.workstation_image.can_execute:
        task_logger.error("Workstation image was not ready to be used")

        service.status = service.FAILED
        service.full_clean()
        service.save()

        return

    if (
        model.objects.active()
        .filter(
            region=service.region,
        )
        .count()
        >= settings.WORKSTATIONS_MAXIMUM_SESSIONS
    ):
        raise RetryStep("Too many sessions are running")

    orchestrator = ECSTaskOrchestrator(**service.orchestrator_kwargs)

    client_token = f"{app_label}-{model_name}-{pk}"

    try:
        service.task_arn = orchestrator.start(
            environment=service.environment,
            client_token=client_token,
        )
    except RetryStep:
        raise
    except Exception as error:
        task_logger.error(error, exc_info=True)

        service.status = service.FAILED
        service.full_clean()
        service.save()

        return
    else:
        service.status = service.STARTED
        service.full_clean()
        service.save()

        update_service.execute_on_commit(**service.task_kwargs)


@lambda_task(retry_on=(LockNotAcquiredException,))
def update_service(*, pk: str | UUID, app_label: str, model_name: str):
    """
    Update the host and ports from ECS

    Takes jobs in the service.STARTED state, waits until they
    are assigned a host and port on ECS, updates the connection information,
    then places them in the service.RUNNING state.
    """
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        service = model.objects.select_for_update(nowait=True).get(pk=pk)

    if service.status != service.STARTED:
        raise RuntimeError("Service is not ready for updating")

    orchestrator = ECSTaskOrchestrator(**service.orchestrator_kwargs)

    try:
        conn_info = orchestrator.get_connection_information(
            task_arn=service.task_arn
        )
    except Exception as error:
        task_logger.error(error, exc_info=True)

        orchestrator.stop(task_arn=service.task_arn)

        service.status = service.FAILED
        service.full_clean()
        service.save()

        return
    else:
        service.host_address = conn_info.host_address
        service.http_port = conn_info.http_port
        service.websocket_port = conn_info.websocket_port

        service.status = service.RUNNING
        service.full_clean()
        service.save()


@lambda_task(retry_on=(LockNotAcquiredException,))
def stop_service(*, pk: str | UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        # We allow all states here (started, stopped, failed, etc.) as the
        # responsibility of this task is to remove the service from ECS
        service = model.objects.select_for_update(nowait=True).get(pk=pk)

    orchestrator = ECSTaskOrchestrator(**service.orchestrator_kwargs)

    if service.task_arn:
        orchestrator.stop(task_arn=service.task_arn)

    service.status = service.STOPPED
    service.full_clean()
    service.save()


@lambda_task
def stop_expired_services(*, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    services_to_stop = (
        model.objects.active()
        .annotate(
            expires=ExpressionWrapper(
                F("claimed_at") + F("maximum_duration"),
                output_field=DateTimeField(),
            )
        )
        .filter(expires__lt=now())
    )

    for service in services_to_stop:
        service.status = model.EXPIRED
        service.save()


class InteractiveAlgorithmLambda:
    def __init__(self, *, arn, qualifier, should_be_active):
        self._arn = arn
        self._qualifier = str(qualifier)
        self._should_be_active = bool(should_be_active)

        self._lambda_client = None

    @property
    def lambda_client(self):
        if self._lambda_client is None:
            self._lambda_client = boto3.client(
                "lambda", region_name=settings.AWS_DEFAULT_REGION
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


@lambda_task
def preload_interactive_algorithms():
    from grandchallenge.reader_studies.models import Question, ReaderStudy
    from grandchallenge.workstations.models import Session

    reader_studies_with_budget = (
        ReaderStudy.objects.with_has_budget()
        .filter(has_budget=True)
        .values_list("pk", flat=True)
    )

    active_interactive_algorithms = (
        Question.objects.filter(
            reader_study__workstation_sessions__status__in=[
                Session.QUEUED,
                Session.STARTED,
                Session.RUNNING,
            ],
            reader_study__pk__in=reader_studies_with_budget,
        )
        .exclude(interactive_algorithm="")
        .values_list("interactive_algorithm", flat=True)
        .distinct()
    )

    consolidation_results = {}

    for lamba_function in settings.INTERACTIVE_ALGORITHMS_LAMBDA_FUNCTIONS[
        "lambda_functions"
    ]:
        interactive_algorithm = InteractiveAlgorithmLambda(
            arn=lamba_function["arn"],
            qualifier=lamba_function["version"],
            should_be_active=lamba_function["internal_name"]
            in active_interactive_algorithms,
        )
        consolidation_results[lamba_function["internal_name"]] = (
            interactive_algorithm.consolidate()
        )

    return consolidation_results


@lambda_task(retry_on=(LockNotAcquiredException,))
def add_image_to_object(  # noqa: C901
    *,
    app_label: str,
    model_name: str,
    object_pk: str | UUID,
    interface_pk: int,
    upload_session_pk: str | UUID | None = None,
    dicom_image_set_upload_pk: str | UUID | None = None,
    linked_task: dict | None = None,
):
    if upload_session_pk is None and dicom_image_set_upload_pk is None:
        raise ValueError(
            "Either upload_session_pk or dicom_image_set_upload_pk must be set."
        )
    if upload_session_pk is not None and dicom_image_set_upload_pk is not None:
        raise ValueError(
            "Only one of upload_session_pk and dicom_image_set_upload_pk should be set."
        )

    from grandchallenge.algorithms.models import Job
    from grandchallenge.archives.models import ArchiveItem
    from grandchallenge.components.models import (
        ComponentInterface,
        ComponentInterfaceValue,
    )
    from grandchallenge.reader_studies.models import DisplaySet

    model = apps.get_model(
        app_label=app_label,
        model_name=model_name,
    )

    try:
        with check_lock_acquired():
            obj = model.objects.select_for_update(nowait=True).get(
                pk=object_pk
            )
    except (ArchiveItem.DoesNotExist, DisplaySet.DoesNotExist):
        task_logger.info(f"Nothing to do: {model_name} no longer exists.")
        return

    interface = ComponentInterface.objects.get(pk=interface_pk)

    if upload_session_pk is not None:
        upload = RawImageUploadSession.objects.get(pk=upload_session_pk)
        expected_status = upload.SUCCESS
        image_lookup_kwargs = {"origin_id": upload_session_pk}
    elif dicom_image_set_upload_pk is not None:
        upload = DICOMImageSetUpload.objects.get(pk=dicom_image_set_upload_pk)
        expected_status = DICOMImageSetUploadStatusChoices.COMPLETED
        image_lookup_kwargs = {
            "dicom_image_set__dicom_image_set_upload_id": dicom_image_set_upload_pk
        }
    else:
        raise ValueError(
            "Either upload_session_pk or dicom_image_set_upload_pk must be set"
        )

    if upload.status != expected_status:
        task_logger.info(
            "Nothing to do: upload session was not in the expected state"
        )
        return

    error_handler = obj.get_error_handler(linked_object=upload)

    try:
        image = Image.objects.get(**image_lookup_kwargs)
    except (Image.DoesNotExist, Image.MultipleObjectsReturned):
        error_handler.handle_error(
            interface=interface,
            error_message="Image imports should result in a single image",
            user=upload.creator,
        )
        task_logger.info("Upload should result in a single image")
        return

    current_value = obj.get_current_value_for_interface(
        interface=interface, user=upload.creator
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
                user=upload.creator,
            )
            task_logger.info(f"Validation failed: {e}")
            return
        except Exception as e:
            error_handler.handle_error(
                interface=interface,
                error_message=SystemErrorMessages.UNEXPECTED_ERROR,
                user=upload.creator,
            )
            task_logger.error(e, exc_info=True)
            return

    try:
        obj.remove_civ(civ=current_value)
        obj.add_civ(civ=civ)
    except CIVNotEditableException as e:
        if isinstance(obj, Job) and obj.status == Job.CANCELLED:
            task_logger.info("Job has been cancelled, exiting")
            return
        else:
            error_handler.handle_error(
                interface=interface,
                error_message=SystemErrorMessages.UNEXPECTED_ERROR,
                user=upload.creator,
            )
            task_logger.error(e, exc_info=True)
            return

    if linked_task is not None:
        task_logger.info("Scheduling linked task")
        SQSLambdaTask.model_validate(linked_task).execute_on_commit()
    else:
        task_logger.info("No linked task, task complete")


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G,
    retry_on=(LockNotAcquiredException,),
    soft_timeout=LONG_TASK_SOFT_TIMEOUT,
    hard_timeout=LONG_TASK_HARD_TIMEOUT,
)
def add_file_to_object(
    *,
    app_label: str,
    model_name: str,
    user_upload_pk: str | UUID,
    object_pk: str | UUID,
    interface_pk: int,
    linked_task: dict | None = None,
):
    from grandchallenge.algorithms.models import Job
    from grandchallenge.archives.models import ArchiveItem
    from grandchallenge.components.models import (
        ComponentInterface,
        ComponentInterfaceValue,
    )
    from grandchallenge.reader_studies.models import DisplaySet

    model = apps.get_model(app_label=app_label, model_name=model_name)

    try:
        with check_lock_acquired():
            obj = model.objects.select_for_update(nowait=True).get(
                pk=object_pk
            )
    except (ArchiveItem.DoesNotExist, DisplaySet.DoesNotExist):
        task_logger.info(f"Nothing to do: {model_name} no longer exists.")
        return

    interface = ComponentInterface.objects.get(pk=interface_pk)
    user_upload = UserUpload.objects.get(pk=user_upload_pk)
    error_handler = obj.get_error_handler(linked_object=user_upload)

    current_value = obj.get_current_value_for_interface(
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
        task_logger.info(f"Validation failed: {e}")
        return
    except Exception as e:
        error_handler.handle_error(
            interface=interface,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
            user=user_upload.creator,
        )
        task_logger.error(e, exc_info=True)
        return

    try:
        obj.remove_civ(civ=current_value)
        obj.add_civ(civ=civ)
    except CIVNotEditableException as e:
        if isinstance(obj, Job) and obj.status == Job.CANCELLED:
            task_logger.info("Job has been cancelled, exiting")
            return
        else:
            error_handler.handle_error(
                interface=interface,
                error_message=SystemErrorMessages.UNEXPECTED_ERROR,
                user=user_upload.creator,
            )
            task_logger.error(e, exc_info=True)
            return

    if linked_task is not None:
        task_logger.info("Scheduling linked task")
        SQSLambdaTask.model_validate(linked_task).execute_on_commit()
    else:
        task_logger.info("No linked task, task complete")


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G, retry_on=(LockNotAcquiredException,)
)
def assign_tarball_from_upload(
    *,
    app_label: str,
    model_name: str,
    tarball_pk: str | UUID,
    field_to_copy: str,
):
    from grandchallenge.components.models import ImportStatusChoices

    TarballModel = apps.get_model(  # noqa: N806
        app_label=app_label, model_name=model_name
    )

    with check_lock_acquired():
        current_tarball = TarballModel.objects.select_for_update(
            nowait=True
        ).get(pk=tarball_pk, import_status=ImportStatusChoices.INITIALIZED)
        peer_tarballs = list(
            current_tarball.get_peer_tarballs().select_for_update(nowait=True)
        )

    current_tarball.user_upload.copy_object(
        to_field=getattr(current_tarball, field_to_copy)
    )

    checksum = get_object_checksum(getattr(current_tarball, field_to_copy))

    if (
        TarballModel.objects.filter(checksum=checksum)
        .exclude(pk=current_tarball.pk)
        .exists()
    ):
        current_tarball.import_status = ImportStatusChoices.FAILED
        current_tarball.status = f"{TarballModel._meta.verbose_name} with this checksum already exists."
        current_tarball.save()

        getattr(current_tarball, field_to_copy).delete()
        current_tarball.user_upload.delete()

        return

    current_tarball.checksum = checksum
    current_tarball.size_in_storage = getattr(
        current_tarball, field_to_copy
    ).size
    current_tarball.import_status = ImportStatusChoices.COMPLETED
    current_tarball.save()

    current_tarball.user_upload.delete()

    # mark as desired version and pass locked peer tarballs directly since else
    # mark_desired_version will fail trying to access the locked tarballs
    current_tarball.mark_desired_version(peer_tarballs=peer_tarballs)


def get_object_checksum(file_field):
    response = file_field.storage.connection.meta.client.head_object(
        Bucket=file_field.storage.bucket.name,
        Key=file_field.name,
        ChecksumMode="ENABLED",
    )

    try:
        checksum = response["ChecksumCRC64NVME"]
        return f"crc64nvme:{hexlify(b64decode(checksum)).decode('utf-8')}"
    except KeyError:
        # The checksums are not calculated on local s3
        task_logger.error("checksum was not calculated", exc_info=True)
        return ""


@lambda_task(retry_on=(LockNotAcquiredException,))
def start_endpoint(*, pk: str | UUID, app_label: str, model_name: str):
    """
    Starts the endpoint on Sagemaker.

    Takes endpoints in the endpoint.QUEUED state, starts them on Sagemaker,
    then places them in the service.RUNNING state.
    """
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        endpoint = model.objects.select_for_update(nowait=True).get(pk=pk)

    if endpoint.status != endpoint.StatusChoices.QUEUED:
        raise RuntimeError(
            "Endpoint is not in the expected state for starting"
        )

    orchestrator = endpoint.orchestrator

    try:
        orchestrator.provision_auxiliary_data()
        orchestrator.create_sagemaker_model()
        orchestrator.create_endpoint_config()
        orchestrator.create_endpoint()
    except Exception:
        task_logger.error("Could not start endpoint", exc_info=True)
        orchestrator.deprovision()
        endpoint.update_status(
            status=endpoint.StatusChoices.FAILED,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )

    else:
        endpoint.update_status(status=endpoint.StatusChoices.STARTED)


@lambda_task(retry_on=(LockNotAcquiredException,))
def handle_endpoint_status_event(*, event: dict):
    from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
        EndpointOrchestrator,
    )

    endpoint_name = EndpointOrchestrator.get_endpoint_name(event=event)
    params = EndpointOrchestrator.get_endpoint_params(
        endpoint_name=endpoint_name
    )

    model = apps.get_model(
        app_label=params.app_label,
        model_name=params.model_name,
    )

    with check_lock_acquired():
        endpoint = model.objects.select_for_update(nowait=True).get(
            pk=params.pk
        )

    if endpoint.status != endpoint.StatusChoices.STARTED:
        # Nothing to do
        return

    orchestrator = endpoint.orchestrator

    try:
        orchestrator.handle_status_event(event=event)
    except ComponentException as error:
        orchestrator.deprovision()
        endpoint.update_status(
            status=endpoint.StatusChoices.FAILED,
            error_message=str(error),
        )
    except Exception:
        task_logger.error("Could not start endpoint", exc_info=True)
        orchestrator.deprovision()
        endpoint.update_status(
            status=endpoint.StatusChoices.FAILED,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
    else:
        endpoint.update_status(status=endpoint.StatusChoices.RUNNING)


@lambda_task(retry_on=(LockNotAcquiredException,))
def stop_endpoint(*, pk: str | UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        endpoint = (
            model.objects.active().select_for_update(nowait=True).get(pk=pk)
        )

    endpoint.orchestrator.deprovision()
    endpoint.update_status(status=endpoint.StatusChoices.STOPPED)
    cancel_active_invocations.execute_on_commit(endpoint_pk=endpoint.pk)


@lambda_task
def stop_expired_endpoints(*, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    endpoints_to_stop = (
        model.objects.active()
        .annotate(
            expires=ExpressionWrapper(
                F("created") + F("maximum_duration"),
                output_field=DateTimeField(),
            )
        )
        .filter(expires__lt=now())
    )

    for endpoint in endpoints_to_stop:
        stop_endpoint.execute_on_commit(**endpoint.task_kwargs)


@lambda_task(retry_on=(LockNotAcquiredException,))
def cancel_active_invocations(*, endpoint_pk: str | UUID):
    from grandchallenge.algorithms.models import Invocation

    with check_lock_acquired():
        invocations = list(
            Invocation.objects.active()
            .select_for_update(nowait=True)
            .filter(endpoint=endpoint_pk)
            .values_list("pk", flat=True)
        )

    Invocation.objects.filter(pk__in=invocations).update(
        status=Invocation.StatusChoices.CANCELLED
    )


@lambda_task(retry_on=(LockNotAcquiredException,))
def provision_invocation_input_data(
    *, pk: str | UUID, app_label: str, model_name: str
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        invocation = model.objects.select_for_update(nowait=True).get(pk=pk)

    if invocation.status == invocation.StatusChoices.CANCELLED:
        # Nothing to do
        return
    elif (
        not invocation.inputs_complete
        or invocation.status != invocation.StatusChoices.QUEUED
    ):
        raise RuntimeError("Invocation is not ready for provisioning")

    if invocation.endpoint.status != invocation.endpoint.StatusChoices.RUNNING:
        raise RuntimeError("Endpoint is not running")

    orchestrator = invocation.orchestrator

    try:
        orchestrator.provision_invocation_input_data(
            input_civs=invocation.inputs.prefetch_related(
                "interface", "image__files"
            ).all(),
        )
    except Exception:
        task_logger.error(
            "Could not provision endpoint for invocation", exc_info=True
        )

        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )

    else:
        invocation.update_status(status=invocation.StatusChoices.PROVISIONED)

        invoke_endpoint.execute_on_commit(**invocation.task_kwargs)


@lambda_task(retry_on=(LockNotAcquiredException,))
def invoke_endpoint(*, pk: str | UUID, app_label: str, model_name: str):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        invocation = (
            model.objects.select_for_update(nowait=True)
            .select_related("endpoint")
            .get(pk=pk)
        )

    if invocation.status == invocation.StatusChoices.CANCELLED:
        # Nothing to do
        return
    elif invocation.status != invocation.StatusChoices.PROVISIONED:
        raise RuntimeError(
            "Invocation is not in the expected state for execution"
        )

    if invocation.endpoint.status != invocation.endpoint.StatusChoices.RUNNING:
        raise RuntimeError("Endpoint is not running")

    orchestrator = invocation.orchestrator

    if not invocation.endpoint.is_linked_to_reader_study:
        invocation.endpoint.keep_alive(duration=orchestrator.time_limit)

    try:
        orchestrator.invoke_endpoint(inference_id=invocation.inference_id)
    except Exception:
        task_logger.error("Could not invoke endpoint", exc_info=True)

        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )

    else:
        invocation.update_status(status=invocation.StatusChoices.EXECUTING)


@lambda_task(retry_on=(LockNotAcquiredException,))
def handle_endpoint_invocation_event(*, event: dict):
    from grandchallenge.components.backends.amazon_sagemaker_endpoint import (
        EndpointOrchestrator,
    )

    inference_id = EndpointOrchestrator.get_inference_id(event=event)
    invocation_params = EndpointOrchestrator.get_invocation_params(
        inference_id=inference_id
    )

    model = apps.get_model(
        app_label=invocation_params.app_label,
        model_name=invocation_params.model_name,
    )

    with check_lock_acquired():
        invocation = model.objects.select_for_update(nowait=True).get(
            pk=invocation_params.pk
        )

    if invocation.status != invocation.StatusChoices.EXECUTING:
        # Nothing to do
        return

    orchestrator = invocation.orchestrator

    try:
        orchestrator.handle_event(event=event)
    except ComponentException as error:
        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=str(error),
            detailed_error_message=error.message_details,
        )
    except Exception as error:
        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error(str(error), exc_info=True)
    else:
        invocation.update_status(
            status=invocation.StatusChoices.EXECUTED,
            invoke_duration=orchestrator.invoke_duration,
        )
        parse_endpoint_invocation_outputs.execute_on_commit(
            **invocation.task_kwargs, event=event
        )


@lambda_task(
    queue=LambdaTaskQueueChoices.MEM8G, retry_on=(LockNotAcquiredException,)
)
def parse_endpoint_invocation_outputs(
    *, pk: str | UUID, app_label: str, model_name: str, event: dict
):
    model = apps.get_model(app_label=app_label, model_name=model_name)

    with check_lock_acquired():
        invocation = model.objects.select_for_update(nowait=True).get(pk=pk)

    if invocation.status == invocation.StatusChoices.CANCELLED:
        # Nothing to do
        return
    elif invocation.status != invocation.StatusChoices.EXECUTED:
        raise RuntimeError("Invocation is not ready for output parsing")

    if invocation.outputs.exists():
        raise RuntimeError("Invocation already has outputs")

    orchestrator = invocation.orchestrator

    try:
        outputs = orchestrator.get_outputs(
            output_interfaces=invocation.algorithm_interface.outputs.all()
        )
    except ComponentException as error:
        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=str(error),
            detailed_error_message=error.message_details,
        )
    except Exception:
        invocation.update_status(
            status=invocation.StatusChoices.FAILURE,
            error_message=SystemErrorMessages.UNEXPECTED_ERROR,
        )
        task_logger.error("Could not parse invocation outputs", exc_info=True)
    else:
        invocation.outputs.add(*outputs)
        invocation.update_status(status=invocation.StatusChoices.SUCCESS)
