"""
Image builder for MetaIO mhd/mha files.

See: https://itk.org/Wiki/MetaIO/Documentation
"""

from pathlib import Path
from typing import Mapping, Sequence, Tuple, Union

import SimpleITK

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.image_builders.metaio_utils import (
    load_sitk_image,
    parse_mh_header,
)
from grandchallenge.cases.image_builders.utils import convert_itk_to_internal
from grandchallenge.cases.models import Image, ImageFile


def image_builder_mhd(path: Path) -> ImageBuilderResult:  # noqa: C901
    """
    Constructs image objects by inspecting files in a directory.

    Parameters
    ----------
    path: Path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    A tuple of
     - all detected images
     - files associated with the detected images
     - path->error message map describing what is wrong with a given file
    """
    element_data_file_key = "ElementDataFile"

    def detect_mhd_file(headers: Mapping[str, Union[str, None]]) -> bool:
        data_file = headers.get(element_data_file_key, None)
        if data_file in [None, "LOCAL"]:
            return False
        data_file_path = (path / Path(data_file)).resolve(strict=False)
        if path not in data_file_path.parents:
            raise ValueError(
                f"{element_data_file_key} references a file which is not in "
                f"the uploaded data folder"
            )
        if not data_file_path.is_file():
            raise ValueError("Data container of mhd file is missing")
        return True

    def detect_mha_file(headers: Mapping[str, Union[str, None]]) -> bool:
        data_file = headers.get(element_data_file_key, None)
        return data_file == "LOCAL"

    def convert_itk_file(
        headers: Mapping[str, Union[str, None]], filename: Path
    ) -> Tuple[Image, Sequence[ImageFile]]:
        try:
            simple_itk_image = load_sitk_image(filename.absolute())
            simple_itk_image: SimpleITK.Image
        except RuntimeError:
            raise ValueError("SimpleITK cannot open file")

        return convert_itk_to_internal(simple_itk_image, name=filename.name)

    new_images = []
    new_image_files = []
    consumed_files = set()
    invalid_file_errors = {}
    for file in path.iterdir():
        try:
            parsed_headers = parse_mh_header(file)
        except ValueError:
            # Maybe add .mhd and .mha files here as "processed" but with errors
            continue

        try:
            is_hd_or_mha = detect_mhd_file(parsed_headers) or detect_mha_file(
                parsed_headers
            )
        except ValueError as e:
            invalid_file_errors[file.name] = str(e)
            continue

        if is_hd_or_mha:
            file_dependency = None
            if parsed_headers[element_data_file_key] != "LOCAL":
                file_dependency = Path(parsed_headers[element_data_file_key])
                if not (path / file_dependency).is_file():
                    invalid_file_errors[file.name] = "cannot find data file"
                    continue

            n_image, n_image_files = convert_itk_file(parsed_headers, file)
            new_images.append(n_image)
            new_image_files += list(n_image_files)

            consumed_files.add(file.name)
            if file_dependency is not None:
                consumed_files.add(str(file_dependency.name))

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map=invalid_file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folder_upload=[],
    )
