import copy
from abc import ABC, abstractmethod

from grandchallenge.notifications.models import Notification, NotificationType


class ErrorHandler(ABC):
    @abstractmethod
    def handle_error(self, *, error_message, user=None, interface=None):
        pass


class JobCIVErrorHandler(ErrorHandler):
    """
    Error handler for CIV validation errors on job creation.
    Handle_error() updates an algorithm job.
    """

    def __init__(self, *args, job, **kwargs):
        super().__init__(*args, **kwargs)

        from grandchallenge.algorithms.models import Job

        if not job or not isinstance(job, Job):
            raise RuntimeError(
                "You need to provide a Job instance to this error handler."
            )

        self._job = job

    def handle_error(self, *, error_message, interface, user=None):
        detailed_error_message = copy.deepcopy(
            self._job.detailed_error_message
        )
        detailed_error_message[interface.title] = error_message
        self._job.update_status(
            status=self._job.CANCELLED,
            error_message="One or more of the inputs failed validation.",
            detailed_error_message=detailed_error_message,
        )


class RawImageUploadSessionErrorHandler(ErrorHandler):
    """
    Error handler for image imports and image validation.
    Handle_error() updates an upload session as well as the linked algorithm job, if provided.
    Use this error handler instead of the JobCIVErrorHandler whenever there is an upload_session object.
    """

    def __init__(self, *args, upload_session, linked_job, **kwargs):
        super().__init__(*args, **kwargs)

        from grandchallenge.algorithms.models import Job

        if not upload_session:
            raise RuntimeError(
                "You need to provide a RawImageUploadSession instance to this error handler."
            )

        if linked_job and not isinstance(linked_job, Job):
            raise RuntimeError("The linked_job needs to be a Job instance.")

        self._upload_session = upload_session
        self._job = linked_job

    def handle_error(self, *, error_message, interface, user=None):
        if self._job:
            self._upload_session.update_status(
                status=self._upload_session.FAILURE,
                error_message=("One or more of the inputs failed validation."),
                detailed_error_message=({interface.title: error_message}),
                linked_object=self._job,
            )
        else:
            self._upload_session.update_status(
                status=self._upload_session.FAILURE,
                error_message=error_message,
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
            kind=NotificationType.NotificationTypeChoices.FILE_COPY_STATUS,
            message=f"Validation for interface {interface.title} failed.",
            description=f"Validation for interface {interface.title} failed: {error_message}",
            actor=user,
        )


class FallbackCIVValidationErrorHandler(ErrorHandler):
    """
    Error handler for errors encountered during CIV validation that are
    not related to a user upload, an upload_session or an algorithm job.
    Use this error handler for CIV validation errors on archive items and display sets.
    Handle_error() sends a CIV_VALIDATION notification.
    """

    def handle_error(self, *, error_message, user, interface):
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.CIV_VALIDATION,
            message=f"Validation for interface {interface.title} failed.",
            description=f"Validation for interface {interface.title} failed: {error_message}",
            actor=user,
        )
