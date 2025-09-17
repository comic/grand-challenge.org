import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import signature
from celery.utils.log import get_task_logger
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.files import File
from django.db import transaction
from django.db.transaction import on_commit
from django.utils._os import safe_join
from django.utils.module_loading import import_string
from panimg import convert, post_process
from panimg.models import PanImgFile, PanImgResult

from grandchallenge.cases.models import (
    Image,
    ImageFile,
    PostProcessImageTask,
    PostProcessImageTaskStatusChoices,
    RawImageUploadSession,
)
from grandchallenge.components.backends.utils import safe_extract
from grandchallenge.components.models import ComponentInterface
from grandchallenge.core.celery import (
    acks_late_2xlarge_task,
    acks_late_micro_short_task,
)
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.core.utils.query import check_lock_acquired
from grandchallenge.uploads.models import UserUpload

logger = get_task_logger(__name__)

POST_PROCESSORS = [
    import_string(p) for p in settings.CASES_POST_PROCESSORS if p
]


class DuplicateFilesException(ValueError):
    pass


def _populate_tmp_dir(tmp_dir, upload_session):
    session_files = [*upload_session.user_uploads.all()]

    populate_provisioning_directory(session_files, tmp_dir)
    extract_files(source_path=tmp_dir)


def populate_provisioning_directory(
    input_files: Sequence[UserUpload], provisioning_dir: Path
):
    """
    Provisions provisioning_dir with the files associated using the given
    list of uploaded files.
    """
    for input_file in input_files:
        dest = Path(safe_join(provisioning_dir, input_file.filename))

        if dest.exists():
            raise DuplicateFilesException("Duplicate files uploaded")

        with open(dest, "wb") as f:
            input_file.download_fileobj(fileobj=f)


def check_compressed_and_extract(*, src_path: Path, checked_paths: set[Path]):
    """Checks if `src_path` is a zip file and if so, extracts it."""
    if src_path in checked_paths:
        return

    checked_paths.add(src_path)

    extracted_dir = src_path.parent / f"{src_path.name}_extracted"
    extracted_dir.mkdir()

    try:
        safe_extract(src=src_path, dest=extracted_dir)
    except (zipfile.BadZipFile, OSError):
        rmtree(extracted_dir)
    else:
        src_path.unlink()
        extracted_dir.rename(src_path)
        extract_files(source_path=src_path, checked_paths=checked_paths)


def extract_files(*, source_path: Path, checked_paths=None):
    if checked_paths is None:
        checked_paths = set()

    for src_path in source_path.rglob("*"):
        check_compressed_and_extract(
            src_path=src_path, checked_paths=checked_paths
        )


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def build_images(  # noqa:C901
    *,
    upload_session_pk,
    linked_app_label,
    linked_model_name,
    linked_object_pk,
    linked_interface_slug,
    linked_task,
):
    """
    Task which analyzes an upload session and attempts to extract and store
    detected images assembled from files uploaded in the image session.

    The task updates the state-filed of the associated
    :class:`RawImageUploadSession` to indicate if it is running or has finished
    computing.

    Results are stored in:
    - `RawImageUploadSession.error_message` if a general error occurred during
        processing.
    - The `RawImageUploadSession.import_result` for file-by-file states.

    Parameters
    ----------
    upload_session_uuid: UUID
        The uuid of the upload sessions that should be analyzed.
    linked_object_pk: UUID
        The pk of the object linked to the upload session, if any. This can be a Job,
        ArchiveItem or DisplaySet.
    linked_app_label:
        The app_label of the linked object.
    linked_model_name:
        The model_name of the linked object.
    linked_interface_slug:
        The slug of the linked interface.
    linked_task:
        The signature of the task to run on success
    """

    with check_lock_acquired():
        upload_session = (
            RawImageUploadSession.objects.prefetch_related("user_uploads")
            .select_for_update(nowait=True)
            .get(pk=upload_session_pk)
        )

    if upload_session.status != upload_session.REQUEUED:
        logger.info(
            "Nothing to do: upload session was not ready for processing"
        )
        return

    def _handle_error(*, error_message):
        logger.info(error_message)
        on_commit(
            handle_build_images_error.signature(
                kwargs={
                    "upload_session_pk": upload_session_pk,
                    "error_message": error_message,
                    "linked_app_label": linked_app_label,
                    "linked_model_name": linked_model_name,
                    "linked_object_pk": linked_object_pk,
                    "linked_interface_slug": linked_interface_slug,
                }
            ).apply_async
        )

    try:
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir).resolve()
            _populate_tmp_dir(tmp_dir, upload_session)
            importer_result = import_images(
                input_directory=tmp_dir, origin=upload_session
            )
            _handle_raw_files(
                consumed_files=importer_result.consumed_files,
                file_errors=importer_result.file_errors,
                base_directory=tmp_dir,
                upload_session=upload_session,
            )
    except RuntimeError as error:
        if "std::bad_alloc" in str(error):
            _handle_error(
                error_message=(
                    "The uploaded images were too large to process, "
                    "please try again with smaller images"
                ),
            )
        else:
            _handle_error(error_message="An unexpected error occurred")
            logger.error(error, exc_info=True)
        return
    except DuplicateFilesException:
        _handle_error(
            error_message=(
                "Duplicate files uploaded, please try again with a unique set of files"
            ),
        )
        return
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        _handle_error(error_message="Time limit exceeded")
        return
    except Exception as error:
        _handle_error(error_message="An unexpected error occurred")
        logger.error(error, exc_info=True)
        return

    if upload_session.image_set.count() > 0:
        upload_session.update_status(status=RawImageUploadSession.SUCCESS)

        if linked_task is not None:
            logger.info("Scheduling linked task")
            on_commit(signature(linked_task).apply_async)
        else:
            logger.info("No linked task, task complete")
    else:
        _handle_error(error_message=upload_session.default_error_message)
        # The session may have been modified so needs to be saved
        upload_session.save()
        return

    logger.info("Deleting associated uploaded files")
    upload_session.user_uploads.all().delete()


@acks_late_micro_short_task(
    retry_on=(LockNotAcquiredException,), delayed_retry=False
)
@transaction.atomic
def handle_build_images_error(
    *,
    upload_session_pk,
    error_message,
    linked_app_label,
    linked_model_name,
    linked_object_pk,
    linked_interface_slug,
):
    with check_lock_acquired():
        upload_session = RawImageUploadSession.objects.select_for_update(
            nowait=True
        ).get(pk=upload_session_pk)

    if linked_object_pk:
        try:
            model = apps.get_model(
                app_label=linked_app_label, model_name=linked_model_name
            )
            with check_lock_acquired():
                linked_object = model.objects.select_for_update(
                    nowait=True
                ).get(pk=linked_object_pk)
        except ObjectDoesNotExist:
            # Linked object may have been deleted
            logger.info(
                f"Linked object {linked_app_label}.{linked_model_name}({linked_object_pk}) does not exist"
            )
            linked_object = None
    else:
        linked_object = None

    try:
        ci = ComponentInterface.objects.get(slug=linked_interface_slug)
    except ObjectDoesNotExist:
        logger.info(f"Linked interface {linked_interface_slug} does not exist")
        ci = None

    error_handler = upload_session.get_error_handler(
        linked_object=linked_object
    )

    error_handler.handle_error(
        interface=ci,
        error_message=error_message,
    )


@dataclass
class ImporterResult:
    new_images: set[Image]
    consumed_files: set[Path]
    file_errors: dict[Path, list[str]]


def import_images(
    *,
    input_directory: Path,
    origin: RawImageUploadSession | None = None,
    builders: Sequence[Callable] | None = None,
    recurse_subdirectories: bool = True,
) -> ImporterResult:
    """
    Creates Image objects from a set of files.

    Parameters
    ----------
    files
        A Set of files that can form one or many Images
    origin
        The RawImageUploadSession (if any) that was the source of these files
    builders
        The Image Builders to use to try and convert these files into Images

    Returns
    -------
        An ImporterResult listing the new images, the consumed files and
        any file errors

    """
    with TemporaryDirectory() as output_directory:
        panimg_result = convert(
            input_directory=input_directory,
            output_directory=output_directory,
            builders=builders,
            post_processors=[],  # Do the post-processing later
            recurse_subdirectories=recurse_subdirectories,
        )

        _check_all_ids(panimg_result=panimg_result)

        django_result = _convert_panimg_to_internal(
            new_images=panimg_result.new_images,
            new_image_files=panimg_result.new_image_files,
        )

        _store_images(
            origin=origin,
            images=django_result.new_images,
            image_files=django_result.new_image_files,
        )

        post_process_image_ids = {
            f.image.pk
            for f in django_result.new_image_files
            if f.image_type == ImageFile.IMAGE_TYPE_TIFF
        }

        for image_id in post_process_image_ids:
            task = PostProcessImageTask(image_id=image_id)
            task.full_clean()
            task.save()

    return ImporterResult(
        new_images=django_result.new_images,
        consumed_files=panimg_result.consumed_files,
        file_errors=panimg_result.file_errors,
    )


def _check_all_ids(*, panimg_result: PanImgResult):
    """
    Check the integrity of the conversion job.

    All new_ids must be new, this will be found when saving the Django objects.
    Every new image must have at least one file associated with it.
    """
    new_ids = {im.pk for im in panimg_result.new_images}
    new_file_ids = {f.image_id for f in panimg_result.new_image_files}

    if new_ids != new_file_ids:
        raise ValidationError(
            "Each new image should have at least 1 file assigned"
        )


@dataclass
class ConversionResult:
    new_images: set[Image]
    new_image_files: set[ImageFile]


def _convert_panimg_to_internal(
    *, new_images, new_image_files
) -> ConversionResult:
    internal_images = set()
    internal_image_files = set()

    for image in new_images:
        image_internal = Image(**asdict(image))

        if image_internal.segments is not None:
            image_internal.segments = list(image_internal.segments)

        internal_images.add(image_internal)

    for image_file in new_image_files:
        image_file_internal = ImageFile(**asdict(image_file))

        image_file_internal.file = File(
            open(image_file_internal.file, "rb"), image_file_internal.file.name
        )

        internal_image_files.add(image_file_internal)

    return ConversionResult(
        new_images=internal_images,
        new_image_files=internal_image_files,
    )


def _store_images(
    *,
    origin: RawImageUploadSession | None,
    images: set[Image],
    image_files: set[ImageFile],
):
    for image in images:
        image.origin = origin
        image.full_clean()
        image.save()

    for obj in image_files:
        obj.full_clean()
        obj.save()


def _handle_raw_files(
    *,
    consumed_files: set[Path],
    file_errors: dict[Path, list[str]],
    base_directory: Path,
    upload_session: RawImageUploadSession,
):
    upload_session.import_result = {
        "consumed_files": [
            str(f.relative_to(base_directory)) for f in consumed_files
        ],
        "file_errors": {
            str(k.relative_to(base_directory)): v
            for k, v in file_errors.items()
            if k not in consumed_files
        },
    }


@acks_late_2xlarge_task(retry_on=(LockNotAcquiredException,))
@transaction.atomic
def execute_post_process_image_task(*, post_process_image_task_pk):
    with check_lock_acquired():
        task = PostProcessImageTask.objects.select_for_update(nowait=True).get(
            pk=post_process_image_task_pk
        )

    if task.status != PostProcessImageTaskStatusChoices.INITIALIZED:
        logger.info(f"Task status is {task.status}, nothing to do")
        return

    try:
        with TemporaryDirectory() as output_directory:
            image_files = ImageFile.objects.filter(image=task.image)

            panimg_files = _download_image_files(
                image_files=image_files, dir=output_directory
            )

            post_processor_result = post_process(
                image_files=panimg_files, post_processors=POST_PROCESSORS
            )

            _check_post_processor_result(
                post_processor_result=post_processor_result, image=task.image
            )

            django_result = _convert_panimg_to_internal(
                new_images=[],
                new_image_files=post_processor_result.new_image_files,
            )

            for obj in django_result.new_image_files:
                obj.full_clean()
                obj.save()

            task.status = PostProcessImageTaskStatusChoices.COMPLETED
            task.save()

    except Exception as error:
        task.status = PostProcessImageTaskStatusChoices.FAILED
        task.save()
        logger.error(error, exc_info=True)
        return


def _download_image_files(*, image_files, dir):
    """
    Downloads a set of image files to a directory

    Returns a set of PanImgFiles that point to the local files
    """
    panimg_files = set()

    for im_file in image_files:
        dest = safe_join(dir, im_file.file.name)
        panimg_files.add(
            PanImgFile(
                image_id=im_file.image.pk,
                image_type=im_file.image_type,
                file=dest,
            )
        )

        # Safe to create directories as safe_join has been used
        Path(dest).parent.mkdir(parents=True, exist_ok=True)

        with im_file.file.open("rb") as fs, open(dest, "wb") as fd:
            for chunk in fs.chunks():
                fd.write(chunk)

    return panimg_files


def _check_post_processor_result(*, post_processor_result, image):
    """Ensure all post processed results belong to the given image"""
    created_ids = {
        str(f.image_id) for f in post_processor_result.new_image_files
    }

    if created_ids not in [{str(image.pk)}, set()]:
        raise RuntimeError("Created image IDs do not match")
