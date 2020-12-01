import os
import tarfile
import zipfile
from collections import defaultdict
from datetime import timedelta
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Dict, Iterable, List, Sequence, Set, Tuple

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from grandchallenge.cases.emails import send_failed_file_import
from grandchallenge.cases.image_builders.dicom import image_builder_dicom
from grandchallenge.cases.image_builders.fallback import image_builder_fallback
from grandchallenge.cases.image_builders.metaio_mhd_mha import (
    image_builder_mhd,
)
from grandchallenge.cases.image_builders.nifti import image_builder_nifti
from grandchallenge.cases.image_builders.tiff import image_builder_tiff
from grandchallenge.cases.image_builders.types import (
    ImageBuilderResult,
    ImporterResult,
)
from grandchallenge.cases.log import logger
from grandchallenge.cases.models import (
    FolderUpload,
    Image,
    ImageFile,
    RawImageFile,
    RawImageUploadSession,
)
from grandchallenge.jqfileupload.widgets.uploader import (
    NotFoundError,
    StagedAjaxFile,
)


class ProvisioningError(Exception):
    pass


def _populate_tmp_dir(tmp_dir, upload_session):
    session_files = upload_session.rawimagefile_set.all()
    session_files, duplicates = remove_duplicate_files(session_files)

    for duplicate in duplicates:  # type: RawImageFile
        duplicate.error = "Filename not unique"
        saf = StagedAjaxFile(duplicate.staged_file_id)
        duplicate.staged_file_id = None
        saf.delete()
        duplicate.consumed = False
        duplicate.save()

    populate_provisioning_directory(session_files, tmp_dir)
    extract_files(tmp_dir)


def populate_provisioning_directory(
    raw_files: Sequence[RawImageFile], provisioning_dir: Path
):
    """
    Provisions provisioning_dir with the files associated using the given
    list of RawImageFile objects.

    Parameters
    ----------
    raw_files:
        The list of RawImageFile that should be saved in the target
        directory.

    provisioning_dir: Path
        The path where to copy the files.

    Raises
    ------
    ProvisioningError:
        Raised when not all files could be copied to the provisioning directory.
    """
    provisioning_dir = Path(provisioning_dir)

    def copy_to_tmpdir(image_file: RawImageFile):
        staged_file = StagedAjaxFile(image_file.staged_file_id)
        if not staged_file.exists:
            raise ValueError(
                f"staged file {image_file.staged_file_id} does not exist"
            )

        with open(provisioning_dir / staged_file.name, "wb") as dest_file:
            with staged_file.open() as src_file:
                buffer_size = 0x10000
                first = True
                buffer = b""
                while first or (len(buffer) >= buffer_size):
                    first = False
                    buffer = src_file.read(buffer_size)
                    dest_file.write(buffer)

    exceptions_raised = 0
    for raw_file in raw_files:
        try:
            copy_to_tmpdir(raw_file)
        except Exception:
            logger.exception(
                f"populate_provisioning_directory exception "
                f"for file: '{raw_file.filename}'"
            )
            exceptions_raised += 1

    if exceptions_raised > 0:
        raise ProvisioningError(
            f"{exceptions_raised} errors occurred during provisioning of the "
            f"image construction directory"
        )


DEFAULT_IMAGE_BUILDERS = [
    image_builder_mhd,
    image_builder_nifti,
    image_builder_dicom,
    image_builder_tiff,
    image_builder_fallback,
]


def remove_duplicate_files(
    session_files: Sequence[RawImageFile],
) -> Tuple[Sequence[RawImageFile], Sequence[RawImageFile]]:
    """
    Filters the given sequence of RawImageFile objects and removes all files
    that have a nun-unique filename.

    Parameters
    ----------
    session_files: Sequence[RawImageFile]
        List of RawImageFile objects thats filenames should be checked for
        uniqueness.

    Returns
    -------
    Two Sequence[RawImageFile]. The first sequence is the filtered session_files
    list, the second list is a list of duplicates that were removed.
    """
    filename_lookup = {}
    duplicates = []
    for file in session_files:
        if file.filename in filename_lookup:
            duplicates.append(file)

            looked_up_file = filename_lookup[file.filename]
            if looked_up_file is not None:
                duplicates.append(looked_up_file)
                filename_lookup[file.filename] = None
        else:
            filename_lookup[file.filename] = file
    return (
        tuple(x for x in filename_lookup.values() if x is not None),
        tuple(duplicates),
    )


def _check_sanity(info, is_tar, path):
    # Check tar files for symlinks and reject upload session if any.
    if is_tar:
        if info.issym() or info.islnk():
            raise ValidationError("(Symbolic) links are not allowed.")
    # Also check for max path length, drop folders when path is too long
    filename_attr = "name" if is_tar else "filename"
    while len(os.path.join(path, getattr(info, filename_attr))) > 4095:
        filename = getattr(info, filename_attr)
        filename = os.path.join(
            *Path(filename).parts[1 : len(Path(filename).parts)]
        )
        setattr(info, filename_attr, filename)


def extract(file, path, is_tar=False):
    """
    Extracts all files in `file` to `path`.

    Parameters
    ----------
    file:
        A zip or tar file.
    path:
        The path to which the contents of `file` are to be extracted.

    """
    list_func = file.getmembers if is_tar else file.infolist
    filename_attr = "name" if is_tar else "filename"
    is_dir_func = "isdir" if is_tar else "is_dir"
    extracted = False
    for info in sorted(list_func(), key=lambda k: getattr(k, filename_attr)):
        # Skip directories
        if getattr(info, is_dir_func)():
            continue

        _check_sanity(info, is_tar, path)
        file.extract(info, path)
        extracted = True
    return extracted


def check_compressed_and_extract(file_path, target_path, checked_paths=None):
    """
    Checks if `file_path` is a zip or tar file and if so, extracts it.

    Parameters
    ----------
    file_path:
        The file path to be checked and possibly extracted.
    target_path:
        The path to which the contents of `file_path` are to be extracted.
    checked_paths:
        Files that have already been extracted.
    """

    def extract_file(fp):
        is_extracted = False
        if tarfile.is_tarfile(fp):
            with tarfile.open(fp) as tf:
                is_extracted = extract(tf, target_path, is_tar=True)
        elif zipfile.is_zipfile(fp):
            with zipfile.ZipFile(fp) as zf:
                is_extracted = extract(zf, target_path)

        # Make sure files have actually been extracted, then delete the archive
        if is_extracted:
            fp.unlink()
        return is_extracted

    if checked_paths is None:
        checked_paths = []
    if file_path in checked_paths:
        return
    checked_paths.append(file_path)

    extracted = extract_file(file_path)

    # check zips in zips
    if extracted:
        for root, _, files in os.walk(target_path):
            for file in files:
                check_compressed_and_extract(
                    Path(os.path.join(root, file)), root, checked_paths
                )


def extract_files(source_path: Path):
    checked_paths = []
    for file_path in source_path.iterdir():
        check_compressed_and_extract(file_path, source_path, checked_paths)


@shared_task
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

    If a job fails due to a RawImageUploadSession.DoesNotExist error, the
    job is queued for a retry (max 15 times).

    Parameters
    ----------
    upload_session_uuid: UUID
        The uuid of the upload sessions that should be analyzed.
    """
    upload_session = RawImageUploadSession.objects.get(
        pk=upload_session_pk
    )  # type: RawImageUploadSession

    if (
        upload_session.status != upload_session.REQUEUED
        or upload_session.rawimagefile_set.filter(consumed=True).exists()
    ):
        raise RuntimeError("Job is not set to be executed.")

    upload_session.status = upload_session.STARTED
    upload_session.save()

    with TemporaryDirectory(prefix="construct_image_volumes-") as tmp_dir:
        tmp_dir = Path(tmp_dir)

        try:
            _populate_tmp_dir(tmp_dir, upload_session)
            _handle_raw_image_files(tmp_dir, upload_session)
        except ProvisioningError as e:
            upload_session.error_message = str(e)
            upload_session.status = upload_session.FAILURE
            upload_session.save()
            return
        except Exception:
            upload_session.error_message = "An unknown error occurred"
            upload_session.status = upload_session.FAILURE
            upload_session.save()
            raise
        else:
            upload_session.status = upload_session.SUCCESS
            upload_session.save()


def _handle_raw_image_files(tmp_dir, upload_session):
    input_files = {
        Path(d[0]).joinpath(f) for d in os.walk(tmp_dir) for f in d[2]
    }

    session_files = [
        RawImageFile.objects.get_or_create(
            filename=str(f.relative_to(tmp_dir)),
            upload_session=upload_session,
        )[0]
        for f in input_files
    ]

    filepath_lookup: Dict[str, RawImageFile] = {
        raw_image_file.staged_file_id
        and os.path.join(
            tmp_dir, StagedAjaxFile(raw_image_file.staged_file_id).name
        )
        or os.path.join(tmp_dir, raw_image_file.filename): raw_image_file
        for raw_image_file in session_files
    }

    importer_result = import_images(files=input_files, origin=upload_session,)

    _handle_raw_files(
        input_files=input_files,
        consumed_files=importer_result.consumed_files,
        file_errors=importer_result.file_errors,
        filepath_lookup=filepath_lookup,
        upload_session=upload_session,
    )

    _delete_session_files(session_files=session_files,)


def import_images(
    *,
    files: Set[Path],
    origin: RawImageUploadSession = None,
    builders: Iterable[Callable] = None,
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

    new_images = set()
    new_image_files = set()
    new_folders = set()
    consumed_files = set()
    file_errors = defaultdict(list)

    created_image_prefix = str(origin.pk)[:8] if origin is not None else ""
    builders = builders if builders is not None else DEFAULT_IMAGE_BUILDERS

    for builder in builders:
        builder_result: ImageBuilderResult = builder(
            files=files - consumed_files,
            created_image_prefix=created_image_prefix,
        )

        new_images |= builder_result.new_images
        new_image_files |= builder_result.new_image_files
        new_folders |= builder_result.new_folders
        consumed_files |= builder_result.consumed_files

        for filepath, msg in builder_result.file_errors.items():
            file_errors[filepath].append(msg)

    _store_images(
        origin=origin,
        images=new_images,
        image_files=new_image_files,
        folders=new_folders,
    )

    return ImporterResult(
        new_images=new_images,
        consumed_files=consumed_files,
        file_errors=file_errors,
    )


def _store_images(
    *,
    origin: RawImageUploadSession,
    images: Set[Image],
    image_files: Set[ImageFile],
    folders: Set[FolderUpload],
):
    with transaction.atomic():
        for image in images:
            image.origin = origin
            image.save()

        for obj in chain(image_files, folders):
            obj.save()


def _handle_raw_files(
    *,
    input_files: Set[Path],
    consumed_files: Set[Path],
    filepath_lookup: Dict[str, RawImageFile],
    file_errors: Dict[Path, List[str]],
    upload_session: RawImageUploadSession,
):
    unconsumed_files = input_files - consumed_files

    n_errors = 0

    for filepath in consumed_files:
        raw_image = filepath_lookup[str(filepath)]
        raw_image.error = None
        raw_image.consumed = True
        raw_image.save()

    for filepath in unconsumed_files:
        raw_file = filepath_lookup[str(filepath)]
        error = "\n".join(file_errors[filepath])
        raw_file.error = (
            f"File could not be processed by any image builder:\n\n{error}"
        )
        n_errors += 1
        raw_file.save()

    if unconsumed_files:
        upload_session.error_message = (
            f"{len(unconsumed_files)} file(s) could not be imported"
        )

        if upload_session.creator and upload_session.creator.email:
            send_failed_file_import(n_errors, upload_session)


def _delete_session_files(*, session_files):
    dicom_group = Group.objects.get(
        name=settings.DICOM_DATA_CREATORS_GROUP_NAME
    )
    users = dicom_group.user_set.values_list("username", flat=True)
    for file in session_files:
        try:
            if file.staged_file_id:
                saf = StagedAjaxFile(file.staged_file_id)

                if (
                    not file.consumed
                    and Path(file.filename).suffix == ".dcm"
                    and getattr(file.creator, "username", None) in users
                ):
                    saf.staged_files.update(
                        timeout=timezone.now() + timedelta(days=90)
                    )
                    continue

                file.staged_file_id = None
                saf.delete()
            file.save()
        except NotFoundError:
            pass
