import shutil
from contextlib import contextmanager

from uuid import UUID
from pathlib import Path
from tempfile import mkdtemp
from typing import Tuple, Sequence, Dict, List

from celery import shared_task
from django.core.files import File
from django.db import transaction
import SimpleITK as sitk
from pipenv.patched.piptools._compat import contextlib

from grandchallenge.cases.log import logger
from grandchallenge.cases.models import RawImageUploadSession, \
    UPLOAD_SESSION_STATE, Image, ImageFile, RawImageFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile, \
    NotFoundError


@contextmanager
def auto_temp_dir(prefix=None):
    temp_dir = mkdtemp(prefix=prefix)
    try:
        yield Path(temp_dir)
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            # This is a problem, but not breaking the regular process. However,
            # lost directories will accumulate and fill up the disk
            logger.error(f"Could not remove temp_dir: {temp_dir}  (dir lost)")


class ProvisioningError(Exception): pass


def image_builder_mhd(path: Path) -> Tuple[Sequence[Image], Sequence[ImageFile], Dict[Path, str]]:
    """
    Constructs image objects by inspecting files in a directory.

    Parameters
    ----------
    path: Path
        Path to a directory that contains all images that were uploaded duing an
        upload session.

    Returns
    -------
    A tuple of
     - all detected images
     - files associated with the detected images
     - path->error message map describing what is wrong with a given file
    """
    def detect_mhd_file(filename: Path) -> bool:
        return filename.suffix.lower() == ".mhd" # TODO

    def detect_mha_file(filename: Path) -> bool:
        return filename.suffix.lower() == ".mha" # TODO

    def convert_itk_file(filename: Path) -> Tuple[Image, Sequence[ImageFile]]:
        simple_itk_image = sitk.ReadImage(str(filename.absolute()))

        with auto_temp_dir() as work_dir:
            work_dir: Path

            sitk.WriteImage(simple_itk_image, str(work_dir / "out.mhd"), True)

            db_image = Image(name=filename.name)
            db_image_files = []
            for _file in work_dir.iterdir():
                with open(_file, "rb") as open_file:
                    db_image_file = ImageFile(
                        image=db_image,
                        file=File(open_file),
                    )
                    db_image_files.append(db_image_file)

        return db_image, db_image_files

    images = []
    image_files = []
    invalid_files = {}
    for file in path.iterdir():
        if detect_mhd_file(file) or detect_mha_file(file):
            n_image, n_image_files = convert_itk_file(file)
            images.append(n_image)
            image_files += list(n_image_files)

    return images, image_files, invalid_files


def populate_provisioning_directory(
        raw_files: Sequence[RawImageFile],
        provisioning_dir: Path):
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
                "staged file {image_file.staged_file_id} does not exist")

        with open(provisioning_dir / staged_file.name, "wb") as dest_file:
            with staged_file.open() as src_file:
                BUFFER_SIZE = 0x10000
                first = True
                while first or (len(buffer) >= BUFFER_SIZE):
                    first = False
                    buffer = src_file.read(BUFFER_SIZE)
                    dest_file.write(buffer)

    # with ThreadPoolExecutor(4) as thread_pool:
    exceptions_raised = 0
    for raw_file in raw_files:
        try:
            copy_to_tmpdir(raw_file)
        except Exception as e:
            exceptions_raised += 1

    if exceptions_raised > 0:
        raise ProvisioningError(
            f"{exceptions_raised} errors occurred during provisioning of the "
            f"image construction directory")


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
    associated_files = [
        _if for _if in all_image_files
        if _if.image == image
    ]

    image.save()
    for af in associated_files:
        af.save()


IMAGE_BUILDER_ALGORITHMS = [
    image_builder_mhd
]


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

    Parameters
    ----------
    upload_session_uuid: UUID
        The uuid of the upload sessions that should be analyzed.

    """
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_uuid)
    upload_session: RawImageUploadSession

    if upload_session.session_state == UPLOAD_SESSION_STATE.queued:
        tmp_dir = Path(mkdtemp(prefix="construct_image_volumes-"))
        try:
            try:
                upload_session.session_state = UPLOAD_SESSION_STATE.running
                upload_session.save()

                session_files = RawImageFile.objects.filter(
                    upload_session=upload_session.pk).all()
                session_files: Tuple[RawImageFile]

                populate_provisioning_directory(session_files, tmp_dir)

                filename_lookup = {
                    StagedAjaxFile(raw_image_file.staged_file_id).name: raw_image_file
                    for raw_image_file in session_files
                }
                unconsumed_filenames = set(filename_lookup.keys())

                collected_images = []
                collected_associated_files = []
                invalid_files = []
                for algorithm in IMAGE_BUILDER_ALGORITHMS:
                    new_images, new_associated_image_files, new_invalid_files = \
                        algorithm(tmp_dir)

                    collected_images += new_images
                    collected_associated_files += new_associated_image_files
                    invalid_files += list(new_invalid_files.keys())

                    for used_file in new_associated_image_files:
                        filename = used_file.file.name
                        unconsumed_filenames.remove(filename)
                    for filename, message in new_invalid_files.items():
                        if filename in unconsumed_filenames:
                            unconsumed_filenames.remove(filename)
                            raw_image = filename_lookup[filename]
                            raw_image.error = str(message)[:128]
                            raw_image.save()

                for image in collected_images:
                    store_image(image, collected_associated_files)
                for unconsumed_filename in unconsumed_filenames:
                    raw_file = filename_lookup[unconsumed_filename]
                    raw_file.error = \
                        "File could not be processed by any image builders"

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
