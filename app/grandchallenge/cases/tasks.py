import zipfile
from dataclasses import asdict, dataclass
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Union,
)

from billiard.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import OperationalError, transaction
from django.db.transaction import on_commit
from django.template.defaultfilters import pluralize
from django.utils._os import safe_join
from panimg import convert
from panimg.models import PanImgResult

from grandchallenge.cases.models import (
    FolderUpload,
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.components.backends.utils import safe_extract
from grandchallenge.jqfileupload.widgets.uploader import (
    NotFoundError,
    StagedAjaxFile,
)
from grandchallenge.notifications.models import Notification, NotificationType
from grandchallenge.uploads.models import UserUpload


class DuplicateFilesException(ValueError):
    pass


def _populate_tmp_dir(tmp_dir, upload_session):
    raw_image_files = upload_session.rawimagefile_set.all()
    session_files = [StagedAjaxFile(f.staged_file_id) for f in raw_image_files]

    session_files += [*upload_session.user_uploads.all()]

    populate_provisioning_directory(session_files, tmp_dir)
    extract_files(source_path=tmp_dir)


def populate_provisioning_directory(
    input_files: Sequence[Union[StagedAjaxFile, UserUpload]],
    provisioning_dir: Path,
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


def check_compressed_and_extract(*, src_path: Path, checked_paths: Set[Path]):
    """Checks if `src_path` is a zip file and if so, extracts it."""
    if src_path in checked_paths:
        return

    checked_paths.add(src_path)

    if zipfile.is_zipfile(src_path):
        extracted_dir = src_path.parent / f"{src_path.name}_extracted"
        extracted_dir.mkdir()

        safe_extract(src=src_path, dest=extracted_dir)

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


@shared_task(**settings.CELERY_TASK_DECORATOR_KWARGS["acks-late-2xlarge"])
def build_images(*, upload_session_pk):
    """
    Task which analyzes an upload session and attempts to extract and store
    detected images assembled from files uploaded in the image session.

    The task updates the state-filed of the associated
    :class:`RawImageUploadSession` to indicate if it is running or has finished
    computing.

    The task also updates the consumed field of the associated
    :class:`RawImageFile` to indicate whether it has been processed or not.

    Results are stored in:
    - `RawImageUploadSession.error_message` if a general error occurred during
        processing.
    - The `RawImageFile.error` field of associated `RawImageFile` objects,
        in case files could not be processed.

    The operation of building images will delete associated `StagedAjaxFile`s
    of analyzed images in order to free up space on the server (only done if the
    function does not error out).

    Parameters
    ----------
    upload_session_uuid: UUID
        The uuid of the upload sessions that should be analyzed.
    """
    session_queryset = RawImageUploadSession.objects.filter(
        pk=upload_session_pk
    ).select_for_update(nowait=True)
    files_queryset = RawImageFile.objects.filter(
        upload_session_id=upload_session_pk
    ).select_for_update(nowait=True)

    with transaction.atomic():
        if files_queryset.filter(consumed=True).exists():
            raise RuntimeError("Session has consumed files.")

        upload_session = session_queryset.get()
        upload_session.status = upload_session.STARTED
        upload_session.save()

    try:
        with transaction.atomic():
            # Acquire locks
            _ = files_queryset.all()
            upload_session = session_queryset.get()

            with TemporaryDirectory() as tmp_dir:
                tmp_dir = Path(tmp_dir)
                _populate_tmp_dir(tmp_dir, upload_session)
                _handle_raw_image_files(tmp_dir, upload_session)

            upload_session.status = upload_session.SUCCESS
            upload_session.save()
    except OperationalError:
        # Could not acquire locks
        raise
    except DuplicateFilesException as e:
        _delete_session_files(upload_session=upload_session)
        upload_session.error_message = str(e)
        upload_session.status = upload_session.FAILURE
        upload_session.save()
    except (SoftTimeLimitExceeded, TimeLimitExceeded):
        upload_session.error_message = "Time limit exceeded."
        upload_session.status = upload_session.FAILURE
        upload_session.save()
    except Exception:
        _delete_session_files(upload_session=upload_session)
        upload_session.error_message = "An unexpected error occurred"
        upload_session.status = upload_session.FAILURE
        upload_session.save()
        raise


def _handle_raw_image_files(tmp_dir, upload_session):
    importer_result = import_images(
        input_directory=tmp_dir, origin=upload_session,
    )

    _handle_raw_files(
        consumed_files=importer_result.consumed_files,
        file_errors=importer_result.file_errors,
        base_directory=tmp_dir,
        upload_session=upload_session,
    )

    _delete_session_files(upload_session=upload_session)


@dataclass
class ImporterResult:
    new_images: Set[Image]
    consumed_files: Set[Path]
    file_errors: Dict[Path, List[str]]


def import_images(
    *,
    input_directory: Path,
    origin: Optional[RawImageUploadSession] = None,
    builders: Optional[Iterable[Callable]] = None,
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
            recurse_subdirectories=recurse_subdirectories,
        )

        _check_all_ids(panimg_result=panimg_result)

        django_result = _convert_panimg_to_django(panimg_result=panimg_result)

        _store_images(
            origin=origin,
            images=django_result.new_images,
            image_files=django_result.new_image_files,
            folders=django_result.new_folders,
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
    Every new image must have at least one file associated with it, and
    new folders can only belong to new images.
    """
    new_ids = {im.pk for im in panimg_result.new_images}
    new_file_ids = {f.image_id for f in panimg_result.new_image_files}
    new_folder_ids = {f.image_id for f in panimg_result.new_folders}

    if new_ids != new_file_ids:
        raise ValidationError(
            "Each new image should have at least 1 file assigned"
        )

    if new_folder_ids - new_ids:
        raise ValidationError("New folder does not belong to a new image")


@dataclass
class ConversionResult:
    new_images: Set[Image]
    new_image_files: Set[ImageFile]
    new_folders: Set[FolderUpload]


def _convert_panimg_to_django(
    *, panimg_result: PanImgResult
) -> ConversionResult:
    new_images = {Image(**asdict(im)) for im in panimg_result.new_images}
    new_image_files = {
        ImageFile(
            image_id=f.image_id,
            image_type=f.image_type,
            file=File(open(f.file, "rb"), f.file.name),
        )
        for f in panimg_result.new_image_files
    }
    new_folders = {
        FolderUpload(**asdict(f)) for f in panimg_result.new_folders
    }

    return ConversionResult(
        new_images=new_images,
        new_image_files=new_image_files,
        new_folders=new_folders,
    )


def _store_images(
    *,
    origin: Optional[RawImageUploadSession],
    images: Set[Image],
    image_files: Set[ImageFile],
    folders: Set[FolderUpload],
):
    for image in images:
        image.origin = origin
        image.full_clean()
        image.save()

    for obj in chain(image_files, folders):
        obj.full_clean()
        obj.save()


def _handle_raw_files(
    *,
    consumed_files: Set[Path],
    file_errors: Dict[Path, List[str]],
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

    if upload_session.import_result["file_errors"]:
        n_errors = len(upload_session.import_result["file_errors"])

        upload_session.error_message = (
            f"{n_errors} file{pluralize(n_errors)} could not be imported"
        )

        if upload_session.creator:
            Notification.send(
                type=NotificationType.NotificationTypeChoices.IMAGE_IMPORT_STATUS,
                message=f"failed with {n_errors} error{pluralize(n_errors)}",
                action_object=upload_session,
            )


def _delete_session_files(*, upload_session):
    for file in upload_session.rawimagefile_set.all():
        try:
            if file.staged_file_id:
                saf = StagedAjaxFile(file.staged_file_id)
                on_commit(saf.delete)
        except NotFoundError:
            pass

        file.delete()

    upload_session.user_uploads.all().delete()
