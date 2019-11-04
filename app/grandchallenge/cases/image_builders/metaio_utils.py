from pathlib import Path

import zlib
from os import PathLike
from typing import Mapping, Union, Optional, List, Any
import SimpleITK as sitk
import SimpleITK._SimpleITK as _sitk

METAIO_IMAGE_TYPES = {
    "MET_NONE": None,
    "MET_ASCII_CHAR": None,
    "MET_CHAR": sitk.sitkInt8,
    "MET_UCHAR": sitk.sitkUInt8,
    "MET_SHORT": sitk.sitkInt16,
    "MET_USHORT": sitk.sitkUInt16,
    "MET_INT": sitk.sitkInt32,
    "MET_UINT": sitk.sitkUInt32,
    "MET_LONG": sitk.sitkInt64,
    "MET_ULONG": sitk.sitkUInt64,
    "MET_LONG_LONG": None,
    "MET_ULONG_LONG": None,
    "MET_FLOAT": sitk.sitkFloat32,
    "MET_DOUBLE": sitk.sitkFloat64,
    "MET_STRING": None,
    "MET_CHAR_ARRAY": sitk.sitkVectorInt8,
    "MET_UCHAR_ARRAY": sitk.sitkVectorUInt8,
    "MET_SHORT_ARRAY": sitk.sitkVectorInt16,
    "MET_USHORT_ARRAY": sitk.sitkVectorUInt16,
    "MET_INT_ARRAY": sitk.sitkVectorInt32,
    "MET_UINT_ARRAY": sitk.sitkVectorUInt32,
    "MET_LONG_ARRAY": sitk.sitkVectorInt64,
    "MET_ULONG_ARRAY": sitk.sitkVectorUInt64,
    "MET_LONG_LONG_ARRAY": None,
    "MET_ULONG_LONG_ARRAY": None,
    "MET_FLOAT_ARRAY": sitk.sitkVectorFloat32,
    "MET_DOUBLE_ARRAY": sitk.sitkVectorFloat64,
    "MET_FLOAT_MATRIX": None,
    "MET_OTHER": None,
}


def parse_mh_header(filename: Path) -> Mapping[str, Union[str, None]]:
    """
    Attempts to parse the headers of an mhd file. This function must be
    secure to safeguard against any untrusted uploaded file.

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

    # attempt to limit number of read headers to prevent overflow attacks
    read_line_limit = 10000

    result = {}
    with open(str(filename), "rb") as f:
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
                line = bin_line.decode("utf-8")
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
                break  # last parsed header...
    return result


def load_sitk_image_with_nd_support_from_headers(
    headers: Mapping[str, Union[str, None]],
    data_file_path: Optional[PathLike] = None,
) -> sitk.Image:
    if headers["ElementDataFile"].strip() == "LOCAL":
        raise ValueError(
            "Expected the MHD header to contain a valid ElementDataFile"
        )

    if data_file_path is None:
        data_file_path = Path(headers["ElementDataFile"])
    if not data_file_path.exists():
        raise IOError("cannot find data file")

    def extract_header_listing(
        property: str, dtype: type = float
    ) -> List[Any]:
        return [dtype(e) for e in headers[property].strip().split(" ")]

    shape = extract_header_listing("DimSize", int)

    num_components = 1
    if "ElementNumberOfChannels" in headers:
        num_components = int(headers["ElementNumberOfChannels"])
        if "_ARRAY" not in headers["ElementType"] and num_components > 1:
            headers["ElementType"] = headers["ElementType"] + "_ARRAY"

    dtype = METAIO_IMAGE_TYPES[headers["ElementType"]]
    if dtype is None:
        error_msg = (
            f"MetaIO datatype: {headers['ElementType']} is not supported"
        )
        raise NotImplementedError(error_msg)

    is_compressed = headers["CompressedData"] == "True"
    with open(str(data_file_path), "rb") as f:
        if not is_compressed:
            s = f.read()
        else:
            s = zlib.decompress(f.read())

    sitk_image = sitk.Image(shape, dtype, num_components)
    _sitk._SetImageFromArray(s, sitk_image)
    sitk_image.SetDirection(extract_header_listing("TransformMatrix"))
    sitk_image.SetSpacing(extract_header_listing("ElementSpacing"))
    sitk_image.SetOrigin(extract_header_listing("Offset"))

    return sitk_image


def load_sitk_image(
    mhd_file: Path, raw_file: Optional[Path] = None
) -> sitk.Image:
    headers = parse_mh_header(mhd_file)
    ndims = int(headers["NDims"])
    if ndims < 4:
        sitk_image = sitk.ReadImage(str(mhd_file))
    elif ndims == 4:
        if raw_file is None:
            raw_file = (
                mhd_file.resolve().parent
                / Path(headers["ElementDataFile"]).name
            )
        sitk_image = load_sitk_image_with_nd_support_from_headers(
            headers=headers, data_file_path=raw_file
        )
    else:
        error_msg = (
            "SimpleITK images with more than 4 dimensions are not supported"
        )
        raise NotImplementedError(error_msg)
    return sitk_image
