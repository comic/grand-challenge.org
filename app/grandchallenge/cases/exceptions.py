class DICOMImportJobError(Exception):

    def __init__(self, message, message_details=None):
        super().__init__(message)
        self.message = message
        self.message_details = message_details


class DICOMImportJobValidationError(DICOMImportJobError):
    """The created image set from a dicom import job is invalid."""


class DICOMImportJobFailedError(DICOMImportJobError):
    """Raised for failed dicom import jobs."""
