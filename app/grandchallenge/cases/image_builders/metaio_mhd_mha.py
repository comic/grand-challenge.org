"""
Image builder for MetaIO mhd/mha files.

See: https://itk.org/Wiki/MetaIO/Documentation
"""

from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Mapping, Sequence, Tuple, Union
from uuid import uuid4

import SimpleITK
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.image_builders.metaio_utils import (
    load_sitk_image,
    parse_mh_header,
)
from grandchallenge.cases.models import Image, ImageFile


def image_builder_mhd(path: Path) -> ImageBuilderResult:  # noqa: C901
    """
    Constructs image objects by inspecting files in a directory.

    Parameters
    ----------
    path: Path
        Path to a directory that contains all images that were uploaded duing
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

        color_space = simple_itk_image.GetNumberOfComponentsPerPixel()
        color_space = {
            1: Image.COLOR_SPACE_GRAY,
            3: Image.COLOR_SPACE_RGB,
            4: Image.COLOR_SPACE_RGBA,
        }.get(color_space, None)
        if color_space is None:
            raise ValueError("Unknown color space for MetaIO image.")

        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)

            pk = uuid4()
            SimpleITK.WriteImage(
                simple_itk_image, str(work_dir / f"{pk}.mhd"), True
            )

            if simple_itk_image.GetDimension() == 4:
                timepoints = simple_itk_image.GetSize()[-1]
            else:
                timepoints = None
            depth = simple_itk_image.GetDepth()
            db_image = Image(
                pk=pk,
                name=filename.name,
                width=simple_itk_image.GetWidth(),
                height=simple_itk_image.GetHeight(),
                depth=depth if depth else None,
                timepoints=timepoints,
                resolution_levels=None,
                color_space=color_space,
            )
            db_image_files = []
            for _file in work_dir.iterdir():
                temp_file = TemporaryFile()
                with open(str(_file), "rb") as open_file:
                    buffer = True
                    while buffer:
                        buffer = open_file.read(1024)
                        temp_file.write(buffer)

                db_image_file = ImageFile(
                    image=db_image,
                    image_type=ImageFile.IMAGE_TYPE_MHD,
                    file=File(temp_file, name=_file.name),
                )
                db_image_files.append(db_image_file)

        return db_image, db_image_files

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
