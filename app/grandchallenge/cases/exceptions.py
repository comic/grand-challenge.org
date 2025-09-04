class DICOMImportJobBaseError(Exception):
    """Base error for handling health imaging dicom import jobs."""


class DICOMImportJobValidationError(DICOMImportJobBaseError):
    """The created image set from a dicom import job is invalid."""


class DICOMImportJobFailedError(DICOMImportJobBaseError):
    """Raised for failed dicom import jobs."""
