import zlib
from pathlib import Path
from typing import Any, List, Mapping, Union

import SimpleITK
import SimpleITK._SimpleITK as _SimpleITK

METAIO_IMAGE_TYPES = {
    "MET_NONE": None,
    "MET_ASCII_CHAR": None,
    "MET_CHAR": SimpleITK.sitkInt8,
    "MET_UCHAR": SimpleITK.sitkUInt8,
    "MET_SHORT": SimpleITK.sitkInt16,
    "MET_USHORT": SimpleITK.sitkUInt16,
    "MET_INT": SimpleITK.sitkInt32,
    "MET_UINT": SimpleITK.sitkUInt32,
    "MET_LONG": SimpleITK.sitkInt64,
    "MET_ULONG": SimpleITK.sitkUInt64,
    "MET_LONG_LONG": None,
    "MET_ULONG_LONG": None,
    "MET_FLOAT": SimpleITK.sitkFloat32,
    "MET_DOUBLE": SimpleITK.sitkFloat64,
    "MET_STRING": None,
    "MET_CHAR_ARRAY": SimpleITK.sitkVectorInt8,
    "MET_UCHAR_ARRAY": SimpleITK.sitkVectorUInt8,
    "MET_SHORT_ARRAY": SimpleITK.sitkVectorInt16,
    "MET_USHORT_ARRAY": SimpleITK.sitkVectorUInt16,
    "MET_INT_ARRAY": SimpleITK.sitkVectorInt32,
    "MET_UINT_ARRAY": SimpleITK.sitkVectorUInt32,
    "MET_LONG_ARRAY": SimpleITK.sitkVectorInt64,
    "MET_ULONG_ARRAY": SimpleITK.sitkVectorUInt64,
    "MET_LONG_LONG_ARRAY": None,
    "MET_ULONG_LONG_ARRAY": None,
    "MET_FLOAT_ARRAY": SimpleITK.sitkVectorFloat32,
    "MET_DOUBLE_ARRAY": SimpleITK.sitkVectorFloat64,
    "MET_FLOAT_MATRIX": None,
    "MET_OTHER": None,
}


def parse_mh_header(filename: Path) -> Mapping[str, Union[str, None]]:
    """
    Attempts to parse the headers of an mhd file.

    This function must be secure to safeguard against any untrusted uploaded
    file.

    Parameters
    ----------
    filename

    Returns
    -------
        The extracted header from the mhd file as key value pairs.

    Raises
    ------
    ValueError
        Raised when the file contains problems making it impossible to
        read.
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


def extract_header_listing(
    property: str, headers: Mapping[str, Union[str, None]], dtype: type = float
) -> List[Any]:
    return [dtype(e) for e in headers[property].strip().split(" ")]


def load_sitk_image_with_nd_support_from_headers(
    mhd_file: Path,
) -> SimpleITK.Image:
    headers = parse_mh_header(mhd_file)
    is_mha = headers["ElementDataFile"].strip() == "LOCAL"
    if is_mha:
        data_file_path = mhd_file
    else:
        data_file_path = (
            mhd_file.resolve().parent / Path(headers["ElementDataFile"]).name
        )
    if not data_file_path.exists():
        raise IOError("cannot find data file")

    shape = extract_header_listing("DimSize", headers=headers, dtype=int)

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
        if is_mha:
            line = ""
            while "ElementDataFile = LOCAL" not in str(line):
                line = f.readline()
        if not is_compressed:
            s = f.read()
        else:
            s = zlib.decompress(f.read())

    sitk_image = SimpleITK.Image(shape, dtype, num_components)
    _SimpleITK._SetImageFromArray(s, sitk_image)
    sitk_image.SetDirection(
        extract_header_listing("TransformMatrix", headers=headers)
    )
    sitk_image.SetSpacing(
        extract_header_listing("ElementSpacing", headers=headers)
    )
    sitk_image.SetOrigin(extract_header_listing("Offset", headers=headers))

    return sitk_image


def load_sitk_image(mhd_file: Path) -> SimpleITK.Image:
    headers = parse_mh_header(mhd_file)
    ndims = int(headers["NDims"])
    if ndims < 4:
        sitk_image = SimpleITK.ReadImage(str(mhd_file))
    elif ndims == 4:
        sitk_image = load_sitk_image_with_nd_support_from_headers(
            mhd_file=mhd_file
        )
    else:
        error_msg = (
            "SimpleITK images with more than 4 dimensions are not supported"
        )
        raise NotImplementedError(error_msg)
    return sitk_image
