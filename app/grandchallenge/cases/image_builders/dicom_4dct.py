import tempfile
from collections import namedtuple
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
    return pydicom.datadict.keyword_for_tag(tag) == "PixelData"


def _get_headers_by_study(path):
    """
    Gets all headers from dicom files found in path.

    Parameters
    ----------
    path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    A dictionary of sorted headers for all dicom image files found within path,
    grouped by study id.
    """
    studies = {}
    for file in path.iterdir():
        if not file.is_file():
            continue
        with file.open("rb") as f:
            try:
                ds = pydicom.filereader.read_partial(
                    f, stop_when=pixel_data_reached
                )
                studies[ds.StudyID] = studies.get(ds.StudyID, {})
                headers = studies[ds.StudyID].get("headers", [])
                headers.append({"file": file, "data": ds})
                studies[ds.StudyID]["headers"] = headers
            except Exception:
                continue
    for key in studies:
        studies[key]["headers"].sort(
            key=lambda x: x["data"].InStackPositionNumber
        )
    return studies


def _validate_dicom_files(path):
    """
    Gets the headers for all dicom files on path and validates them.

    Parameters
    ----------
    path
        Path to a directory that contains all images that were uploaded during
        an upload session.

    Returns
    -------
    A list of `dicom_dataset` named tuples per study, consisting of:
     - Headers for all dicom image files for the study
     - Number of time points
     - Number of slices per time point

    Any study with an inconsistent amount of slices per time point is discarded.
    """
    studies = _get_headers_by_study(path)
    result = []
    dicom_dataset = namedtuple(
        "dicom_dataset", ["headers", "n_time", "n_slices"]
    )
    for key in studies:
        headers = studies[key]["headers"]
        if not headers:
            continue
        n_time = headers[-1]["data"].TemporalPositionIndex
        if len(headers) % n_time > 0:
            continue
        n_slices = len(headers) // n_time
        result.append(
            dicom_dataset(headers=headers, n_time=n_time, n_slices=n_slices)
        )
    del studies
    return result


def image_builder_dicom_4dct(path: Path) -> ImageBuilderResult:
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
    studies = _validate_dicom_files(path)
    new_images = []
    new_image_files = []
    consumed_files = []
    for dicom_ds in studies:

        consumed_files += [d["file"].name for d in dicom_ds.headers]
        ref_file = pydicom.dcmread(str(dicom_ds.headers[0]["file"]))

        direction = np.eye(4, dtype=np.float)
        try:
            # Try to extract the direction from the file
            sitk_ref = SimpleITK.ReadImage(str(dicom_ds.headers[0]["file"]))
            # The direction per slice is a 3x3 matrix, so we add the time
            # dimension ourselves
            dims = sitk_ref.GetDimension()
            _direction = np.reshape(sitk_ref.GetDirection(), (dims, dims))
            direction[:dims, :dims] = _direction
        except Exception:
            pass
        pixel_dims = (
            dicom_ds.n_time,
            dicom_ds.n_slices,
            int(ref_file.Rows),
            int(ref_file.Columns),
        )
        dtype = ref_file.pixel_array.dtype
        dcm_array = np.zeros(pixel_dims, dtype=dtype)

        # Additional Meta data Contenttimes and Exposures
        content_times = []
        exposures = []

        for index, partial in enumerate(dicom_ds.headers):
            ds = pydicom.dcmread(str(partial["file"]))
            dcm_array[
                index // dicom_ds.n_slices, index % dicom_ds.n_slices, :, :
            ] = ds.pixel_array
            if index % dicom_ds.n_slices == 0:
                content_times.append(str(ds.ContentTime))
                exposures.append(str(ds.Exposure))
            del ds

        shape = dcm_array.shape[::-1]

        # Write the numpy array to a file, so there is no need to keep it in memory
        # anymore. Then create a SimpleITK image from it.
        with tempfile.NamedTemporaryFile() as temp:
            temp.seek(0)
            temp.write(dcm_array.tostring())
            temp.flush()
            temp.seek(0)
            del dcm_array
            img = SimpleITK.Image(shape, NUMPY_IMAGE_TYPES[dtype.name], 1)
            SimpleITK._SimpleITK._SetImageFromArray(temp.read(), img)

        # Set Image Spacing, Origin and Direction
        sitk_origin = tuple(
            (float(i) for i in ref_file.ImagePositionPatient)
        ) + (0.0,)
        sitk_direction = tuple(direction.flatten())
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
        new_images.append(n_image)
        new_image_files += n_image_files

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors_map={},
        new_images=new_images,
        new_image_files=new_image_files,
        new_folder_upload=[],
    )
