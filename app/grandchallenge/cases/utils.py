import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from panimg.image_builders.metaio_utils import load_sitk_image


def get_sitk_image(*, image):
    """Return the image that belongs to this model instance as an SimpleITK image.

    Requires that exactly one MHD/RAW file pair is associated with the model.
    Otherwise it wil raise a MultipleObjectsReturned or ObjectDoesNotExist
    exception.

    Returns
    -------
        A SimpleITK image

    """
    files = [i for i in image.get_metaimage_files() if i is not None]

    file_size = 0
    for file in files:
        if not file.file.storage.exists(name=file.file.name):
            raise FileNotFoundError(f"No file found for {file.file}")

        # Add up file sizes of mhd and raw file to get total file size
        file_size += file.file.size

    # Check file size to guard for out of memory error
    if file_size > settings.MAX_SITK_FILE_SIZE:
        raise OSError(
            f"File exceeds maximum file size. (Size: {file_size}, Max: {settings.MAX_SITK_FILE_SIZE})"
        )

    with TemporaryDirectory() as tempdirname:
        for file in files:
            with file.file.open("rb") as infile, open(
                Path(tempdirname) / Path(file.file.name).name, "wb"
            ) as outfile:
                buffer = True
                while buffer:
                    buffer = infile.read(1024)
                    outfile.write(buffer)

        try:
            hdr_path = Path(tempdirname) / Path(files[0].file.name).name
            sitk_image = load_sitk_image(hdr_path)
        except RuntimeError as e:
            logging.error(f"Failed to load SimpleITK image with error: {e}")
            raise

    return sitk_image
