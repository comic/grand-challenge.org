from collections import namedtuple
from math import isclose
from pathlib import Path
from typing import Set

import SimpleITK
import numpy as np
import pydicom

from panimg.image_builders.utils import convert_itk_to_internal
from panimg.types import ImageBuilderResult

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

OPTIONAL_METADATA_FIELDS = (
    # These fields will be included in the output mha file
    "Laterality",
    "PatientID",
    "PatientName",
    "PatientBirthDate",
    "PatientAge",
    "PatientSex",
    "StudyDate",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "StudyDescription",
    "SliceThickness",
    "WindowCenter",
    "WindowWidth",
)


def pixel_data_reached(tag, vr, length):
    return pydicom.datadict.keyword_for_tag(tag) == "PixelData"


def _get_headers_by_study(files: Set[Path]):
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
    errors = {}
    indices = {}

    for file in files:
        if not file.is_file():
            continue
        with file.open("rb") as f:
            try:
                ds = pydicom.filereader.read_partial(
                    f, stop_when=pixel_data_reached
                )
                dims = f"{ds.Rows}x{ds.Columns}"
                key = f"{ds.StudyInstanceUID}-{dims}"
                studies[key] = studies.get(key, {})
                indices[ds.StudyInstanceUID] = indices.get(
                    ds.StudyInstanceUID, {}
                )
                index = indices[ds.StudyInstanceUID].get(dims)
                if index is None:
                    index = (
                        max(list(indices[ds.StudyInstanceUID].values()) + [-1])
                        + 1
                    )
                    indices[ds.StudyInstanceUID][dims] = index
                headers = studies[key].get("headers", [])
                headers.append({"file": file, "data": ds})
                studies[key]["index"] = index
                studies[key]["headers"] = headers
            except Exception as e:
                errors[file] = format_error(e)

    for key in studies:
        studies[key]["headers"].sort(
            key=lambda x: int(x["data"].InstanceNumber)
        )
    return studies, errors


def format_error(message):
    return f"Dicom image builder: {message}"


def _validate_dicom_files(files: Set[Path]):
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
    studies, errors = _get_headers_by_study(files)
    result = []
    dicom_dataset = namedtuple(
        "dicom_dataset", ["headers", "n_time", "n_slices", "index"]
    )
    for key in studies:
        headers = studies[key]["headers"]
        index = studies[key]["index"]
        if not headers:
            continue
        data = headers[-1]["data"]
        n_time = getattr(data, "TemporalPositionIndex", None)
        n_slices = max(len(headers), int(getattr(data, "NumberOfFrames", 0)))
        # Not a 4d dicom file
        if n_time is None:
            result.append(
                dicom_dataset(
                    headers=headers,
                    n_time=n_time,
                    n_slices=n_slices,
                    index=index,
                )
            )
            continue
        if len(headers) % n_time > 0:
            for d in headers:
                errors[d["file"]] = format_error(
                    "Number of slices per time point differs"
                )
            continue
        n_slices = n_slices // n_time
        result.append(
            dicom_dataset(
                headers=headers, n_time=n_time, n_slices=n_slices, index=index,
            )
        )
    del studies
    return result, errors


def _extract_direction(dicom_ds, direction):
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
    return direction


def _process_dicom_file(  # noqa: C901
    *, dicom_ds, created_image_prefix, output_directory
):
    ref_file = pydicom.dcmread(str(dicom_ds.headers[0]["file"]))
    ref_origin = tuple(
        float(i) for i in getattr(ref_file, "ImagePositionPatient", (0, 0, 0))
    )
    dimensions = 4 if dicom_ds.n_time and dicom_ds.n_time > 1 else 3
    direction = np.eye(dimensions, dtype=float)
    direction = _extract_direction(dicom_ds, direction)
    pixel_dims = (
        dicom_ds.n_slices,
        int(ref_file.Rows),
        int(ref_file.Columns),
    )
    if dimensions == 4:
        pixel_dims = (dicom_ds.n_time,) + pixel_dims

    # Additional Meta data Contenttimes and Exposures
    content_times = []
    exposures = []
    origin = None
    origin_diff = np.array((0, 0, 0), dtype=float)
    n_diffs = 0
    for partial in dicom_ds.headers:
        ds = partial["data"]
        if "ImagePositionPatient" in ds:
            file_origin = np.array(ds.ImagePositionPatient, dtype=float)
            if origin is not None:
                diff = file_origin - origin
                origin_diff = origin_diff + diff
                n_diffs += 1
            origin = file_origin
    avg_origin_diff = tuple(origin_diff / n_diffs)
    try:
        z_i = avg_origin_diff[2]
    except IndexError:
        z_i = 1.0

    samples_per_pixel = int(getattr(ref_file, "SamplesPerPixel", 1))
    img = _create_itk_from_dcm(
        content_times=content_times,
        dicom_ds=dicom_ds,
        dimensions=dimensions,
        exposures=exposures,
        pixel_dims=pixel_dims,
        z_i=z_i,
        samples_per_pixel=samples_per_pixel,
    )

    if origin is None:
        origin = (0.0, 0.0, 0.0)
    sitk_origin = ref_origin if z_i >= 0.0 else tuple(origin)
    z_i = np.abs(z_i) if not np.isnan(z_i) else 1.0

    if "PixelSpacing" in ref_file:
        x_i, y_i = (float(x) for x in ref_file.PixelSpacing)
    else:
        x_i = y_i = 1.0

    sitk_spacing = (x_i, y_i, z_i)
    if dimensions == 4:
        sitk_spacing += (1.0,)
        sitk_origin += (0.0,)

    sitk_direction = tuple(direction.flatten())
    img.SetDirection(sitk_direction)
    img.SetSpacing(sitk_spacing)
    img.SetOrigin(sitk_origin)

    if dimensions == 4:
        # Set Additional Meta Data
        img.SetMetaData("ContentTimes", " ".join(content_times))
        img.SetMetaData("Exposures", " ".join(exposures))

    for f in OPTIONAL_METADATA_FIELDS:
        if getattr(ref_file, f, False):
            img.SetMetaData(f, str(getattr(ref_file, f)))

    # Convert the SimpleITK image to our internal representation
    return convert_itk_to_internal(
        simple_itk_image=img,
        name=f"{created_image_prefix}-{dicom_ds.headers[0]['data'].StudyInstanceUID}-{dicom_ds.index}",
        output_directory=output_directory,
    )


def _create_itk_from_dcm(
    *,
    content_times,
    dicom_ds,
    dimensions,
    exposures,
    pixel_dims,
    z_i,
    samples_per_pixel,
):
    apply_slope = any(
        not isclose(float(getattr(h["data"], "RescaleSlope", 1.0)), 1.0)
        for h in dicom_ds.headers
    )
    apply_intercept = any(
        not isclose(float(getattr(h["data"], "RescaleIntercept", 0.0)), 0.0)
        for h in dicom_ds.headers
    )
    apply_scaling = apply_slope or apply_intercept
    is_rgb = samples_per_pixel > 1
    if apply_scaling:
        np_dtype = np.float32
    else:
        np_dtype = np.short
    if samples_per_pixel > 1:
        pixel_dims += (samples_per_pixel,)
    dcm_array = None
    use_pixel_array = False

    for index, partial in enumerate(dicom_ds.headers):
        ds = pydicom.dcmread(str(partial["file"]))

        if apply_scaling:
            pixel_array = float(
                getattr(ds, "RescaleSlope", 1)
            ) * ds.pixel_array + float(getattr(ds, "RescaleIntercept", 0))
        else:
            pixel_array = ds.pixel_array

        if (
            len(pixel_array.shape) == dimensions
            or pixel_array.shape == pixel_dims
        ):
            use_pixel_array = True
            del ds
            break
        if dcm_array is None:
            dcm_array = np.zeros(pixel_dims, dtype=np_dtype)

        z_index = index if z_i >= 0 else len(dicom_ds.headers) - index - 1

        if dimensions == 4:
            dcm_array[
                index // dicom_ds.n_slices, z_index % dicom_ds.n_slices, :, :
            ] = pixel_array
            if index % dicom_ds.n_slices == 0:
                content_times.append(str(ds.ContentTime))
                exposures.append(str(ds.Exposure))
        else:
            dcm_array[z_index % dicom_ds.n_slices, :, :] = pixel_array

        del ds
    if use_pixel_array:
        img = SimpleITK.GetImageFromArray(pixel_array, isVector=is_rgb)
    else:
        img = SimpleITK.GetImageFromArray(dcm_array, isVector=is_rgb)
    return img


def image_builder_dicom(
    *, files: Set[Path], output_directory: Path, created_image_prefix: str = ""
) -> ImageBuilderResult:
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
    studies, file_errors = _validate_dicom_files(files)
    new_images = set()
    new_image_files = set()
    consumed_files = set()
    for dicom_ds in studies:
        try:
            n_image, n_image_files = _process_dicom_file(
                dicom_ds=dicom_ds,
                created_image_prefix=created_image_prefix,
                output_directory=output_directory,
            )
            new_images.add(n_image)
            new_image_files |= set(n_image_files)
            consumed_files |= {d["file"] for d in dicom_ds.headers}
        except Exception as e:
            for d in dicom_ds.headers:
                file_errors[d["file"]] = format_error(e)

    return ImageBuilderResult(
        consumed_files=consumed_files,
        file_errors=file_errors,
        new_images=new_images,
        new_image_files=new_image_files,
        new_folders=set(),
    )
