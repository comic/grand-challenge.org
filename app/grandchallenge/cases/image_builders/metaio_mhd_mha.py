"""
Image builder for MetaIO mhd/mha files.

See: https://itk.org/Wiki/MetaIO/Documentation
"""

from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile
from typing import Mapping, Union, Sequence, Tuple

import SimpleITK as sitk
from django.core.files import File

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.models import Image, ImageFile


def parse_mh_header(filename: Path) -> Mapping[str, Union[str, None]]:
    """
    Attempts to parse the headers of an mhd file. This function must be
    secure to safeguard agains any untrusted uploaded file.

    Parameters
    ----------
    filename

    Returns
    -------

    Raises
    ------
    ValueError:
        raised when the file contains problems making it impossible to
        read
    """
    read_line_limit = 10000  # attempt to limit numer of read headers to prevent overflow attacks

    result = {}
    with open(filename, 'rb') as f:
        bin_line = True
        while bin_line is not None:
            read_line_limit -= 1
            if read_line_limit < 0:
                raise ValueError("Files contains too many header lines")

            bin_line = f.readline(10000)
            if not bin_line:
                bin_line = None
                continue
            if len(bin_line) >= 10000:
                raise ValueError("Line length is too long")

            try:
                line = bin_line.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("Header contains invalid UTF-8")
            else:
                # Clean line endings
                line = line.rstrip("\n\r")
                if line.strip():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        result[key.strip()] = value.strip()
                    else:
                        result[line.strip()] = None
            if "ElementDataFile" in result:
                break # last parsed header...
    return result


def image_builder_mhd(path: Path) -> ImageBuilderResult:
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
    ELEMENT_DATA_FILE_KEY = "ElementDataFile"

    def detect_mhd_file(headers: Mapping[str, Union[str, None]]) -> bool:
        data_file = headers.get(ELEMENT_DATA_FILE_KEY, None)
        if data_file in [None, "LOCAL"]:
            return False
        data_file_path = (path / Path(data_file)).resolve(strict=False)
        if path not in data_file_path.parents:
            raise ValueError(
                f"{ELEMENT_DATA_FILE_KEY} references a file which is not in "
                f"the uploaded data folder")
        if not data_file_path.is_file():
            raise ValueError("Data container of mhd file is missing")
        return True

    def detect_mha_file(headers: Mapping[str, Union[str, None]]) -> bool:
        data_file = headers.get(ELEMENT_DATA_FILE_KEY, None)
        return data_file == "LOCAL"

    def convert_itk_file(
            headers: Mapping[str, Union[str, None]],
            filename: Path) -> Tuple[Image, Sequence[ImageFile]]:
        try:
            simple_itk_image = sitk.ReadImage(str(filename.absolute()))
        except RuntimeError:
            raise ValueError("SimpleITK cannot open file")

        with TemporaryDirectory() as work_dir:
            work_dir = Path(work_dir)

            sitk.WriteImage(simple_itk_image, str(work_dir / "out.mhd"), True)

            db_image = Image(name=filename.name)
            db_image_files = []
            for _file in work_dir.iterdir():
                temp_file = TemporaryFile()
                with open(_file, "rb") as open_file:
                    buffer = True
                    while buffer:
                        buffer = open_file.read(1024)
                        temp_file.write(buffer)

                db_image_file = ImageFile(
                    image=db_image,
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
            is_hd_or_mha = \
                detect_mhd_file(parsed_headers) or \
                detect_mha_file(parsed_headers)
        except ValueError as e:
            invalid_file_errors[file.name] = str(e)
            continue

        if is_hd_or_mha:
            file_dependency = None
            if parsed_headers[ELEMENT_DATA_FILE_KEY] != "LOCAL":
                file_dependency = Path(parsed_headers[ELEMENT_DATA_FILE_KEY])
                if not (path / file_dependency).is_file():
                    invalid_file_errors[file.name] = \
                        "cannot find data file"
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
    )


