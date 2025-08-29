class DICOMImportJobError(Exception):

    def __init__(self, message, message_details=None):
        super().__init__(message)
        self.message = message
        self.message_details = message_details


class DICOMImportJobFailedError(DICOMImportJobError):
    """Raised for failed dicom import jobs."""
