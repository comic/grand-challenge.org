import re
import zlib
from pathlib import Path
from typing import Any, Dict, List, Mapping, Pattern, Tuple, Union

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

FLOAT_MATCH_REGEXP: Pattern = re.compile(
    r"^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$"
)
FLOAT_LIST_MATCH_REGEXP: Pattern = re.compile(
    r"^([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)"
    r"(\s[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)*$"
)
CONTENT_TIMES_LIST_MATCH_REGEXP: Pattern = re.compile(
    r"^((2[0-3]|[0-1]\d)[0-5]\d[0-5]\d(\.\d\d\d)?)"
    r"(\s(2[0-3]|[0-1]\d)[0-5]\d[0-5]\d(\.\d\d\d)?)*$"
)

ADDITIONAL_HEADERS: Dict[str, Pattern] = {
    "Exposures": FLOAT_LIST_MATCH_REGEXP,
    "ContentTimes": CONTENT_TIMES_LIST_MATCH_REGEXP,
    "t0": FLOAT_MATCH_REGEXP,
    "t1": FLOAT_MATCH_REGEXP,
}

HEADERS_MATCHING_NUM_TIMEPOINTS: List[str] = ["Exposures", "ContentTimes"]

EXPECTED_HEADERS: List[str] = [
    "ObjectType",
    "NDims",
    "BinaryData",
    "BinaryDataByteOrderMSB",
    "CompressedData",
    "CompressedDataSize",
    "TransformMatrix",
    "Offset",
    "CenterOfRotation",
    "AnatomicalOrientation",
    "ElementSpacing",
    "ElementNumberOfChannels",
    "DimSize",
    "ElementType",
    "ElementDataFile",
]


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
                extract_key_value_pairs(line, result)
            if "ElementDataFile" in result:
                break  # last parsed header...
    return result


def extract_key_value_pairs(line: str, result: Dict[str, str]):
    line = line.rstrip("\n\r")
    if line.strip():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
        else:
            result[line.strip()] = None


def extract_header_listing(
    property: str, headers: Mapping[str, Union[str, None]], dtype: type = float
) -> List[Any]:
    return [dtype(e) for e in headers[property].strip().split(" ")]


def load_sitk_image_with_nd_support(mhd_file: Path,) -> SimpleITK.Image:
    headers = parse_mh_header(mhd_file)
    is_mha = headers["ElementDataFile"].strip() == "LOCAL"
    data_file_path = resolve_mh_data_file_path(headers, is_mha, mhd_file)

    shape = extract_header_listing("DimSize", headers=headers, dtype=int)

    dtype, num_components = determine_mh_components_and_dtype(headers)

    sitk_image = create_sitk_img_from_mh_data(
        data_file_path, dtype, headers, is_mha, num_components, shape
    )

    sitk_image.SetDirection(
        extract_header_listing("TransformMatrix", headers=headers)
    )
    sitk_image.SetSpacing(
        extract_header_listing("ElementSpacing", headers=headers)
    )
    sitk_image.SetOrigin(extract_header_listing("Offset", headers=headers))

    return sitk_image


def determine_mh_components_and_dtype(
    headers: Mapping[str, Union[str, None]]
) -> Tuple[int, int]:
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
    return dtype, num_components


def resolve_mh_data_file_path(
    headers: Mapping[str, Union[str, None]], is_mha: bool, mhd_file: Path
) -> Path:
    if is_mha:
        data_file_path = mhd_file
    else:
        data_file_path = (
            mhd_file.resolve().parent / Path(headers["ElementDataFile"]).name
        )
    if not data_file_path.exists():
        raise IOError("cannot find data file")
    return data_file_path


def create_sitk_img_from_mh_data(
    data_file_path: Path,
    dtype: int,
    headers: Mapping[str, Union[str, None]],
    is_mha: bool,
    num_components: int,
    shape,
) -> SimpleITK.Image:
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
    return sitk_image


def validate_and_clean_additional_mh_headers(
    headers: Mapping[str, Union[str, None]]
) -> Mapping[str, Union[str, None]]:
    cleaned_headers = {}
    for key, value in headers.items():
        if key in EXPECTED_HEADERS:
            cleaned_headers[key] = value
        else:
            if key in ADDITIONAL_HEADERS:
                match_pattern = ADDITIONAL_HEADERS[key]
                if not re.match(match_pattern, value):
                    raise ValueError(
                        f"Invalid data type found for "
                        f"additional header key: {key}"
                    )
                cleaned_headers[key] = value
        if key in HEADERS_MATCHING_NUM_TIMEPOINTS:
            validate_list_data_matches_num_timepoints(
                headers=headers, key=key, value=value
            )

    return cleaned_headers


def validate_list_data_matches_num_timepoints(
    headers: Mapping[str, Union[str, None]], key: str, value: str
):
    num_timepoints = len(value.split(" "))
    expected_timepoints = (
        int(headers["DimSize"].split(" ")[3])
        if int(headers["NDims"]) >= 4
        else 1
    )
    if num_timepoints != expected_timepoints:
        raise ValueError(
            f"Found {num_timepoints} values for {key}, "
            f"but expected {expected_timepoints} (1/timepoint)"
        )


def add_additional_mh_headers_to_sitk_image(
    sitk_image: SimpleITK.Image, headers: Mapping[str, Union[str, None]]
):
    cleaned_headers = validate_and_clean_additional_mh_headers(headers)
    for header in ADDITIONAL_HEADERS:
        if header in cleaned_headers:
            value = cleaned_headers[header]
            if isinstance(value, (list, tuple)):
                value = " ".format([str(v) for v in value])
            else:
                value = str(value)
            sitk_image.SetMetaData(header, value)


def load_sitk_image(mhd_file: Path) -> SimpleITK.Image:
    headers = parse_mh_header(mhd_file)
    headers = validate_and_clean_additional_mh_headers(headers=headers)
    ndims = int(headers["NDims"])
    if ndims < 4:
        sitk_image = SimpleITK.ReadImage(str(mhd_file))
        for key in sitk_image.GetMetaDataKeys():
            if key not in ADDITIONAL_HEADERS:
                sitk_image.EraseMetaData(key)
    elif ndims <= 4:
        sitk_image = load_sitk_image_with_nd_support(mhd_file=mhd_file)
    else:
        error_msg = (
            "SimpleITK images with more than 4 dimensions are not supported"
        )
        raise NotImplementedError(error_msg)
    add_additional_mh_headers_to_sitk_image(
        sitk_image=sitk_image, headers=headers
    )
    return sitk_image
