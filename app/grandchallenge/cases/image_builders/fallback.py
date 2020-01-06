from pathlib import Path

import SimpleITK
import numpy as np
from PIL import Image
from django.core.exceptions import ValidationError

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.image_builders.utils import convert_itk_to_internal


def image_builder_fallback(path: Path) -> ImageBuilderResult:
    """
    Constructs image objects by inspecting files in a directory.

    Parameters
    ----------
    path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    An `ImageBuilder` object consisting of:
     - a list of filenames for all files consumed by the image builder
     - a list of detected images
     - a list files associated with the detected images
     - path->error message map describing what is wrong with a given file
    """
    errors = {}
    new_images = []
    new_image_files = []
    consumed_files = []
    for file_path in path.iterdir():
        try:
            img = Image.open(file_path)

            if img.format.lower() not in ["jpeg", "png"]:
                raise ValidationError(
                    f"Unsupported image format: {img.format}"
                )

            img_array = np.array(img)
            is_vector = img.mode != "L"
            img = SimpleITK.GetImageFromArray(img_array, isVector=is_vector)
            n_image, n_image_files = convert_itk_to_internal(
                img, name=file_path.name, use_spacing=False
            )
            new_images.append(n_image)
            new_image_files += n_image_files
            consumed_files.append(file_path.name)
        except (IOError, ValidationError):
            errors[file_path.name] = "Not a valid image file"

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folder_upload=[],
    )
