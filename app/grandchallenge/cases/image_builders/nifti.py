from pathlib import Path
from typing import Set

import SimpleITK

from grandchallenge.cases.image_builders.types import ImageBuilderResult
from grandchallenge.cases.image_builders.utils import convert_itk_to_internal


def format_error(message):
    return f"NifTI image builder: {message}"


def image_builder_nifti(*, files: Set[Path], **_) -> ImageBuilderResult:
    """
    Constructs image objects from files in NifTI format (nii/nii.gz)

    Parameters
    ----------
    files
        Path to images that were uploaded during an upload session.

    Returns
    -------
    An `ImageBuilder` object consisting of:
     - a list of filenames for all files consumed by the image builder
     - a list of detected images
     - a list files associated with the detected images
     - path->error message map describing what is wrong with a given file
    """
    errors = {}
    new_images = set()
    new_image_files = set()
    consumed_files = set()
    for file in files:
        if not (file.name.endswith(".nii") or file.name.endswith(".nii.gz")):
            continue

        try:
            reader = SimpleITK.ImageFileReader()
            reader.SetImageIO("NiftiImageIO")
            reader.SetFileName(str(file.absolute()))
            img: SimpleITK.Image = reader.Execute()
        except RuntimeError:
            errors[file] = format_error("Not a valid NifTI image file")
            continue

        try:
            n_image, n_image_files = convert_itk_to_internal(
                img, name=file.name
            )
            new_images.add(n_image)
            new_image_files |= set(n_image_files)
            consumed_files.add(file)
        except ValueError as e:
            errors[file] = format_error(e)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors=errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folders=set(),
    )
