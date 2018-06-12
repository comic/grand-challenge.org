from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import mkdtemp
from typing import Tuple, Sequence, Dict
from uuid import UUID

from celery import shared_task
from pip._vendor.distlib._backport import shutil

from grandchallenge.cases.models import RawImageUploadSession, \
    UPLOAD_SESSION_STATE, Image, ImageFile, RawImageFile
from grandchallenge.jqfileupload.widgets.uploader import StagedAjaxFile


class ProvisioningError(Exception): pass


def mhd_construction(path: Path) -> Tuple[Sequence[Image], Sequence[ImageFile], Dict[Path, str]]:
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
    images = []
    image_files = []
    invalid_files = []
    for file in path.iterdir():
        pass
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

    with ThreadPoolExecutor(4) as thread_pool:
        results = [
            thread_pool.submit(copy_to_tmpdir, rfile)
            for rfile in raw_files
        ]

    exceptions_raised = 0
    for result in results:
        exception = result.exception()
        if exception is not None:
            exceptions_raised += 1
    if exceptions_raised > 0:
        raise ProvisioningError(
            f"{exceptions_raised} errors occurred during provisioning of the "
            f"image construction directory")


@shared_task
def build_images(upload_session_uuid: UUID):
    upload_session = RawImageUploadSession.objects.get(pk=upload_session_uuid)
    upload_session: RawImageUploadSession

    if upload_session.session_state == UPLOAD_SESSION_STATE.queued:
        tmp_dir = Path(mkdtemp(prefix="construct_image_volumes-"))
        try:
            try:
                upload_session.session_state = UPLOAD_SESSION_STATE.running
                upload_session.save()

                IMAGE_CONSTRUCTION_ALGORITHMS = [
                    mhd_construction
                ]

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
                for algorithm in IMAGE_CONSTRUCTION_ALGORITHMS:
                    new_images, new_associated_image_files, new_invalid_files = \
                        algorithm()

                    collected_images += new_images
                    collected_associated_files += new_associated_image_files
                    invalid_files += list(new_invalid_files.keys())

                    for used_file in new_associated_image_files:
                        filename = used_file.file.name
                        unconsumed_filenames.remove(filename)

                    for filename, message in new_invalid_files.iteritems():
                        if filename in unconsumed_filenames:
                            unconsumed_filenames.remove(filename)
                            raw_image = filename_lookup[filename]
                            raw_image.error = str(message)[:128]
                            raw_image.save()
                # TODO: save results to database
            except Exception as e:
                upload_session.error_message = str(e)
        finally:
            if tmp_dir is None:
                shutil.rmtree(tmp_dir)

            upload_session.session_state = UPLOAD_SESSION_STATE.stopped
            upload_session.save()

