import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Tuple, Sequence
from uuid import UUID

from celery import shared_task
from django.db import transaction

from grandchallenge.algorithms.models import Job
from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.image_builders.metaio_mhd_mha import (
    image_builder_mhd
)
from grandchallenge.cases.log import logger
from grandchallenge.cases.models import (
    RawImageUploadSession,
    UPLOAD_SESSION_STATE,
    Image,
    ImageFile,
    RawImageFile,
)
from grandchallenge.jqfileupload.widgets.uploader import (
    StagedAjaxFile,
    NotFoundError,
)


class ProvisioningError(Exception):
    pass


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
                BUFFER_SIZE = 0x10000
                first = True
                while first or (len(buffer) >= BUFFER_SIZE):
                    first = False
                    buffer = src_file.read(BUFFER_SIZE)
                    dest_file.write(buffer)

    exceptions_raised = 0
    for raw_file in raw_files:
        try:
            copy_to_tmpdir(raw_file)
        except Exception as e:
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


@transaction.atomic
def store_image(image: Image, all_image_files: Sequence[ImageFile]):
    """
    Stores an image in the database in a single transaction (or fails
    accordingly). Associated image files are extracted from the
    all_image_files argument and stored together with the image itself
    in a single transaction.

    Parameters
    ----------
    image: :class:`Image`
        The image to store. The actual image files that are stored are extracted
        from the second argument.

    all_image_files: list of :class:`ImageFile`
        An unordered list of ImageFile objects that might or might not belong
        to the image provided as the first argument. The function automatically
        extracts related images from the all_image_files argument to store
        alongside the given image.
    """
    associated_files = [_if for _if in all_image_files if _if.image == image]
    image.save()
    for af in associated_files:
        af.save()


IMAGE_BUILDER_ALGORITHMS = [image_builder_mhd]


def remove_duplicate_files(
    session_files: Sequence[RawImageFile]
) -> Tuple[Sequence[RawImageFile], Sequence[RawImageFile]]:
    """
    Filters the given sequence of RawImageFile objects and removes all files
    that have a nun-unqie filename.

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


@shared_task
def build_images(upload_session_uuid: UUID):
    """
    Task which analyzes an upload session and attempts to extract and store
    detected images assembled from files uploaded in the image session.

    The task updates the state-filed of the associated
    :class:`RawImageUploadSession` to indicate if it is running or has finished
    computing.

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
        pk=upload_session_uuid
    )  # type: RawImageUploadSession

    if upload_session.session_state == UPLOAD_SESSION_STATE.queued:
        tmp_dir = Path(mkdtemp(prefix="construct_image_volumes-"))
        try:
            try:
                upload_session.session_state = UPLOAD_SESSION_STATE.running
                upload_session.save()

                session_files = RawImageFile.objects.filter(
                    upload_session=upload_session.pk
                ).all()  # type: Tuple[RawImageFile]

                session_files, duplicates = remove_duplicate_files(
                    session_files
                )
                for duplicate in duplicates:  # type: RawImageFile
                    duplicate.error = "Filename not unique"
                    saf = StagedAjaxFile(duplicate.staged_file_id)
                    duplicate.staged_file_id = None
                    saf.delete()
                    duplicate.save()

                populate_provisioning_directory(session_files, tmp_dir)

                filename_lookup = {
                    StagedAjaxFile(
                        raw_image_file.staged_file_id
                    ).name: raw_image_file
                    for raw_image_file in session_files
                }
                unconsumed_filenames = set(filename_lookup.keys())

                collected_images = []
                collected_associated_files = []
                for algorithm in IMAGE_BUILDER_ALGORITHMS:
                    algorithm_result = algorithm(
                        tmp_dir
                    )  # type: ImageBuilderResult

                    collected_images += list(algorithm_result.new_images)
                    collected_associated_files += list(
                        algorithm_result.new_image_files
                    )

                    for filename in algorithm_result.consumed_files:
                        if filename in unconsumed_filenames:
                            unconsumed_filenames.remove(filename)
                    for (
                        filename,
                        msg,
                    ) in algorithm_result.file_errors_map.items():
                        if filename in unconsumed_filenames:
                            unconsumed_filenames.remove(filename)
                            raw_image = filename_lookup[
                                filename
                            ]  # type: RawImageFile
                            raw_image.error = str(msg)[:256]
                            raw_image.save()

                for image in collected_images:
                    image.origin = upload_session
                    store_image(image, collected_associated_files)

                for unconsumed_filename in unconsumed_filenames:
                    raw_file = filename_lookup[unconsumed_filename]
                    raw_file.error = (
                        "File could not be processed by any image builder"
                    )

                if upload_session.imageset:
                    upload_session.imageset.images.add(*collected_images)

                if upload_session.annotationset:
                    upload_session.annotationset.images.add(*collected_images)

                if upload_session.algorithm:
                    for image in collected_images:
                        Job.objects.create(
                            algorithm=upload_session.algorithm, image=image
                        )

                if upload_session.algorithm_result:
                    upload_session.algorithm_result.images.add(
                        *collected_images
                    )

                # Delete any touched file data
                for file in session_files:
                    try:
                        saf = StagedAjaxFile(file.staged_file_id)
                        file.staged_file_id = None
                        saf.delete()
                        file.save()
                    except NotFoundError:
                        pass

            except Exception as e:
                upload_session.error_message = str(e)
        finally:
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir)

            upload_session.session_state = UPLOAD_SESSION_STATE.stopped
            upload_session.save()
