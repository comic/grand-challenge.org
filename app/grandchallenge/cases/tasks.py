import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import transaction
from django.db.transaction import on_commit
from django.utils._os import safe_join
from django.utils.module_loading import import_string
from panimg import convert, post_process
from panimg.models import PanImgFile, PanImgResult

from grandchallenge.archives.models import ArchiveItem
from grandchallenge.cases.models import Image, ImageFile, RawImageUploadSession
from grandchallenge.components.backends.utils import safe_extract
from grandchallenge.components.models import ComponentInterface
from grandchallenge.components.tasks import lock_model_instance
from grandchallenge.core.celery import acks_late_2xlarge_task
from grandchallenge.core.exceptions import LockNotAcquiredException
from grandchallenge.reader_studies.models import DisplaySet
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
    linked_app_label=None,
    linked_model_name=None,
    linked_object_pk=None,
    linked_interface_slug=None,
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
    """

    upload_session = lock_model_instance(
        pk=upload_session_pk,
        app_label=RawImageUploadSession._meta.app_label,
        model_name=RawImageUploadSession._meta.model_name,
    )

    if linked_object_pk:
        try:
            linked_object = lock_model_instance(
                pk=linked_object_pk,
                app_label=linked_app_label,
                model_name=linked_model_name,
            )
        except (ArchiveItem.DoesNotExist, DisplaySet.DoesNotExist):
            # users can delete archive items and display sets before this task runs
            logger.info(
                f"Nothing to do here: {linked_model_name} no longer exists."
            )
            upload_session.update_status(
                status=RawImageUploadSession.CANCELLED,
                error_message="Image processing canceled. "
                f"The associated {linked_model_name} not longer exists.",
            )
            return
    else:
        linked_object = None

    if linked_interface_slug:
        ci = ComponentInterface.objects.get(slug=linked_interface_slug)
    else:
        ci = None

    error_handler = upload_session.get_error_handler(
        linked_object=linked_object
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

        if upload_session.image_set.count() == 0:
            error_handler.handle_error(
                interface=ci,
                error_message=upload_session.default_error_message,
            )
        else:
            upload_session.update_status(status=RawImageUploadSession.SUCCESS)
    except RuntimeError as error:
        if "std::bad_alloc" in str(error):
            error_handler.handle_error(
                interface=ci,
                error_message=(
                    "The uploaded images were too large to process, "
                    "please try again with smaller images"
                ),
            )
            logger.info("Images were too large to process")
        else:
            error_handler.handle_error(
                interface=ci,
                error_message="An unexpected error occurred",
            )
            logger.error("An unexpected error occurred", exc_info=True)
    except DuplicateFilesException:
        error_handler.handle_error(
            interface=ci,
            error_message=(
                "Duplicate files uploaded, please try again with a unique set of files"
            ),
        )
        logger.info("Could not process duplicate input files")
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        error_handler.handle_error(
            interface=ci,
            error_message="Time limit exceeded",
        )
        logger.info("Time limit exceeded")
    except Exception:
        error_handler.handle_error(
            interface=ci,
            error_message="An unexpected error occurred",
        )
        logger.error("An unexpected error occurred", exc_info=True)
    finally:
        upload_session.user_uploads.all().delete()
        logger.info("User uploads deleted")


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

        for image in django_result.new_images:
            on_commit(
                post_process_image.signature(
                    kwargs={"image_pk": image.pk}
                ).apply_async
            )

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


@acks_late_2xlarge_task
@transaction.atomic
def post_process_image(*, image_pk):
    with TemporaryDirectory() as output_directory:
        image_files = ImageFile.objects.filter(
            image__pk=image_pk, post_processed=False
        ).select_for_update(nowait=True)

        # Acquire the locks
        image_files = list(image_files)

        panimg_files = _download_image_files(
            image_files=image_files, dir=output_directory
        )

        post_processor_result = post_process(
            image_files=panimg_files, post_processors=POST_PROCESSORS
        )

        _check_post_processor_result(
            post_processor_result=post_processor_result, image_pk=image_pk
        )

        django_result = _convert_panimg_to_internal(
            new_images=[],
            new_image_files=post_processor_result.new_image_files,
        )

        _store_post_processed_images(
            image_files=image_files,
            new_image_files=django_result.new_image_files,
        )


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


def _check_post_processor_result(*, post_processor_result, image_pk):
    """Ensure all post processed results belong to the given image"""
    created_ids = {
        str(f.image_id) for f in post_processor_result.new_image_files
    }

    if created_ids not in [{str(image_pk)}, set()]:
        raise RuntimeError("Created image IDs do not match")


def _store_post_processed_images(*, image_files, new_image_files):
    """Save the post processed files"""
    for im_file in image_files:
        im_file.post_processed = True
        im_file.save(update_fields=["post_processed"])

    for obj in new_image_files:
        obj.full_clean()
        obj.save()
