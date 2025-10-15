import copy
import logging
from abc import ABC, abstractmethod

from grandchallenge.notifications.models import (
    Notification,
    NotificationTypeChoices,
)

logger = logging.getLogger(__name__)


class ErrorHandler(ABC):
    @abstractmethod
    def handle_error(self, *, error_message, user=None, interface=None):
        pass


class ComponentJobCIVErrorHandler(ErrorHandler):

    def __init__(self, *args, job, **kwargs):
        super().__init__(*args, **kwargs)
        self._job = job

    def handle_error(self, *, error_message, interface=None, user=None):
        if interface:
            detailed_error_message = copy.deepcopy(
                self._job.detailed_error_message
            )
            detailed_error_message[interface.title] = error_message
            self._job.update_status(
                status=self._job.CANCELLED,
                error_message="One or more of the inputs failed validation.",
                detailed_error_message=detailed_error_message,
            )
        else:
            self._job.update_status(
                status=self._job.CANCELLED, error_message=error_message
            )


class JobCIVErrorHandler(ComponentJobCIVErrorHandler):
    """
    Error handler for CIV validation errors on job creation.
    Handle_error() updates an algorithm job.
    """

    def __init__(self, *args, job, **kwargs):
        super().__init__(*args, job=job, **kwargs)

        from grandchallenge.algorithms.models import Job

        if not job or not isinstance(job, Job):
            raise RuntimeError(
                "You need to provide a Job instance to this error handler."
            )


class EvaluationCIVErrorHandler(ComponentJobCIVErrorHandler):
    """
    Error handler for CIV validation errors on evaluation creation.
    Handle_error() updates an evaluation.
    """

    def __init__(self, *args, job, **kwargs):
        super().__init__(*args, job=job, **kwargs)

        from grandchallenge.evaluation.models import Evaluation

        if not job or not isinstance(job, Evaluation):
            raise RuntimeError(
                "You need to provide a Evaluation instance to this error handler."
            )

    def handle_error(self, *, error_message, interface=None, user=None):
        # for evaluations don't share the actual error message
        # as it could lead information to challenge participants
        # instead, log the error to sentry
        logger.error(error_message, exc_info=True)

        # and send a generic error message to the user
        error_message = "Input validation failed"

        super().handle_error(
            error_message=error_message, interface=interface, user=user
        )


class RawImageUploadSessionErrorHandler(ErrorHandler):
    """
    Error handler for image imports and image validation.
    Handle_error() updates an upload session as well as the linked algorithm job, if provided.
    Use this error handler instead of the JobCIVErrorHandler whenever there is an upload_session object.
    """

    def __init__(self, *args, upload_session, linked_object, **kwargs):
        super().__init__(*args, **kwargs)

        if not upload_session:
            raise RuntimeError(
                "You need to provide a RawImageUploadSession instance to this error handler."
            )

        self._upload_session = upload_session
        self._linked_object = linked_object

    def handle_error(self, *, error_message, interface, user=None):
        from grandchallenge.evaluation.models import Evaluation

        if self._linked_object:
            if isinstance(self._linked_object, Evaluation):
                logger.error(error_message, exc_info=True)
                error_message = "Input validation failed"

            self._upload_session.update_status(
                status=self._upload_session.FAILURE,
                error_message=("One or more of the inputs failed validation."),
                detailed_error_message=({interface.title: error_message}),
                linked_object=self._linked_object,
            )
        else:
            self._upload_session.update_status(
                status=self._upload_session.FAILURE,
                error_message=error_message,
            )


class DICOMImageSetUploadErrorHandler(ErrorHandler):
    """
    Error handler for DICOM image imports and image validation.
    Handle_error() updates a dicom image set upload as well as the linked algorithm job, if provided.
    Use this error handler instead of the JobCIVErrorHandler whenever there is an upload_session object.
    """

    def __init__(self, *args, dicom_image_set_upload, linked_object, **kwargs):
        super().__init__(*args, **kwargs)

        from grandchallenge.cases.models import DICOMImageSetUpload
        from grandchallenge.components.models import ComponentJob

        if not dicom_image_set_upload or not isinstance(
            dicom_image_set_upload, DICOMImageSetUpload
        ):
            raise RuntimeError(
                "You need to provide a DICOMImageSetUpload instance to this error handler."
            )

        self._dicom_image_set_upload = dicom_image_set_upload

        if isinstance(linked_object, ComponentJob):
            self._linked_object = linked_object
        else:
            self._linked_object = None

    def handle_error(self, *, error_message, interface=None, user=None):
        if interface:
            detailed_error_message = {interface.title: error_message}
            self._dicom_image_set_upload.mark_failed(
                error_message="One or more of the inputs failed validation.",
                detailed_error_message=detailed_error_message,
            )
        else:
            self._dicom_image_set_upload.mark_failed(
                error_message=error_message,
            )

        if self._linked_object:
            linked_error_handler = self._linked_object.get_error_handler()
            linked_error_handler.handle_error(
                error_message=error_message,
                interface=interface,
                user=user,
            )


class UserUploadCIVErrorHandler(ErrorHandler):
    """
    Error handler for file imports and file content validation
    that are not algorithm job related.
    Handle_error() sends a FILE_COPY_STATUS notification.
    For file validation errors related to an algorithm job,
    use the JobCIVErrorHandler instead.
    """

    def __init__(self, *args, user_upload, **kwargs):
        super().__init__(*args, **kwargs)

        if not user_upload:
            raise RuntimeError(
                "You need to provide a UserUpload instance to this error handler."
            )

        self._user_upload = user_upload

    def handle_error(self, *, error_message, user, interface):
        Notification.send(
            kind=NotificationTypeChoices.FILE_COPY_STATUS,
            message=f"Validation for socket {interface.title} failed.",
            description=f"Validation for socket {interface.title} failed: {error_message}",
            actor=user,
        )


class FallbackCIVValidationErrorHandler(ErrorHandler):
    """
    Error handler for errors encountered during CIV validation that are
    not related to a user upload, an upload_session or an algorithm job.
    Use this error handler for CIV validation errors on archive items and display sets.
    Handle_error() sends a CIV_VALIDATION notification.
    """

    def handle_error(self, *, error_message, user, interface=None):
        if interface:
            Notification.send(
                kind=NotificationTypeChoices.CIV_VALIDATION,
                message=f"Validation for socket {interface.title} failed.",
                description=f"Validation for socket {interface.title} failed: {error_message}",
                actor=user,
            )
        else:
            Notification.send(
                kind=NotificationTypeChoices.CIV_VALIDATION,
                message=error_message,
                description=error_message,
                actor=user,
            )
