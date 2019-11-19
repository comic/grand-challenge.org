import tempfile
from pathlib import Path

import SimpleITK
import numpy as np
import pydicom

from grandchallenge.cases.image_builders import ImageBuilderResult
from grandchallenge.cases.image_builders.utils import convert_itk_to_internal

NUMPY_IMAGE_TYPES = {
    "character": SimpleITK.sitkUInt8,
    "uint8": SimpleITK.sitkUInt8,
    "uint16": SimpleITK.sitkUInt16,
    "uint32": SimpleITK.sitkUInt32,
    "uint64": SimpleITK.sitkUInt64,
    "int8": SimpleITK.sitkInt8,
    "int16": SimpleITK.sitkInt16,
    "int32": SimpleITK.sitkInt32,
    "int64": SimpleITK.sitkInt64,
    "float32": SimpleITK.sitkFloat32,
    "float64": SimpleITK.sitkFloat64,
}


def pixel_data_reached(tag, vr, length):
    if pydicom.datadict.keyword_for_tag(tag) == "PixelData":
        return True
    return False


def _get_headers(path):
    """
    Gets all headers from dicom files found in path.

    Parameters
    ----------
    path: Path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    Sorted headers for all dicom image files found within path.

    Raises
    ------
    ValueError
        If not all files are dicom files or if the study id varies between
        files.
    """
    headers = []
    study_id = None
    for file in path.iterdir():
        if not file.is_file():
            continue
        with file.open("rb") as f:
            try:
                ds = pydicom.filereader.read_partial(
                    f, stop_when=pixel_data_reached
                )
                headers.append({"file": str(file), "data": ds})
                if study_id and ds.StudyID != study_id:
                    raise ValueError("Study ID is inconsistent across files")
            except Exception:
                raise ValueError("Invalid dicom file passed.")
    headers.sort(key=lambda x: x["data"].InStackPositionNumber)
    return headers


def _validate_dicom_files(path):
    """
    Gets the headers for all dicom files on path and validates them.

    Parameters
    ----------
    path: Path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    A tuple of
     - Headers for all dicom image files found within path
     - Number of time points
     - Number of slices per time point

    Raises
    ------
    ValueError
        If the number of slices varies between time points.
    """
    headers = _get_headers(path)
    if not headers:
        raise ValueError("No dicom headers could be parsed")
    n_time = headers[-1]["data"].TemporalPositionIndex
    if len(headers) % n_time > 0:
        raise ValueError("Number of slices per time point varies")
    n_slices = len(headers) // n_time
    return headers, n_time, n_slices


def image_builder_dicom_4dct(path: Path) -> ImageBuilderResult:
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
    try:
        headers, n_time, n_slices = _validate_dicom_files(path)
    except ValueError as e:
        return ImageBuilderResult(
            consumed_files=[],
            file_errors_map={file.name: str(e) for file in path.iterdir()},
            new_images=[],
            new_image_files=[],
            new_folder_upload=[],
        )

    consumed_files = [d["file"] for d in headers]
    ref_file = pydicom.dcmread(headers[0]["file"])

    pixel_dims = (n_time, n_slices, int(ref_file.Rows), int(ref_file.Columns))
    dtype = ref_file.pixel_array.dtype
    dcm_array = np.zeros(pixel_dims, dtype=dtype)

    # Additional Meta data Contenttimes and Exposures
    content_times = []
    exposures = []

    for index, partial in enumerate(headers):
        ds = pydicom.dcmread(partial["file"])
        dcm_array[index // n_slices, index % n_slices, :, :] = ds.pixel_array
        if index % n_slices == 0:
            content_times.append(str(ds.ContentTime))
            exposures.append(str(ds.Exposure))
        del ds

    # Headers are no longer needed, delete them to free memory
    del headers
    shape = dcm_array.shape[::-1]

    # Write the numpy array to a file, so there is no need to keep it in memory
    # anymore. Then create a SimpleITK image from it
    with tempfile.NamedTemporaryFile() as temp:
        temp.seek(0)
        temp.write(dcm_array.tostring())
        temp.flush()
        temp.seek(0)
        del dcm_array
        img = SimpleITK.Image(shape, NUMPY_IMAGE_TYPES[dtype.name], 1)
        SimpleITK._SimpleITK._SetImageFromArray(temp.read(), img)

    # Set Image Spacing, Origin and Direction
    sitk_origin = tuple((float(i) for i in ref_file.ImagePositionPatient)) + (
        0.0,
    )
    sitk_direction = tuple(np.eye(4, dtype=np.float).flatten())
    x_i, y_i = (float(x) for x in ref_file.PixelSpacing)
    z_i = float(ref_file.SliceThickness)
    sitk_spacing = (x_i, y_i, z_i, 1.0)

    img.SetDirection(sitk_direction)
    img.SetSpacing(sitk_spacing)
    img.SetOrigin(sitk_origin)

    # Set Additional Meta Data
    img.SetMetaData("ContentTimes", " ".join(content_times))
    img.SetMetaData("Exposures", " ".join(exposures))

    # Convert the SimpleITK image to our internal representation
    n_image, n_image_files = convert_itk_to_internal(img)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map={},
        new_images=[n_image],
        new_image_files=n_image_files,
        new_folder_upload=[],
    )
