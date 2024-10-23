from grandchallenge.notifications.models import Notification, NotificationType


class ErrorHandler:
    def handle_error(self, *, error_message, user=None, interface=None):
        raise NotImplementedError("Subclasses must implement this method")


class JobCIVErrorHandler(ErrorHandler):

    def __init__(self, job):
        from grandchallenge.algorithms.models import Job

        if not job or not isinstance(job, Job):
            raise RuntimeError(
                "You need to provide a Job instance to this error handler."
            )

        self._job = job

    def handle_error(self, *, error_message, interface, user=None):
        detailed_error_message = self._job.detailed_error_message.copy()
        detailed_error_message[interface.title] = error_message
        self._job.update_status(
            status=self._job.CANCELLED,
            error_message="One or more of the inputs failed validation.",
            detailed_error_message=detailed_error_message,
        )


class RawImageUploadSessionCIVErrorHandler(ErrorHandler):

    def __init__(self, upload_session, linked_job):
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
        self._upload_session.update_status(
            status=self._upload_session.FAILURE,
            error_message=("One or more of the inputs failed validation."),
            detailed_error_message=({interface.title: error_message}),
            linked_object=self._job,
        )


class RawImageUploadSessionBuildErrorHandler(ErrorHandler):

    def __init__(self, upload_session):
        if not upload_session:
            raise RuntimeError(
                "You need to provide a RawImageUploadSession instance to this error handler."
            )

        self._upload_session = upload_session

    def handle_error(self, *, error_message, user=None, interface=None):
        self._upload_session.update_status(
            status=self._upload_session.FAILURE,
            error_message=error_message,
        )


class UserUploadCIVErrorHandler(ErrorHandler):
    def __init__(self, user_upload):
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


class SystemCIVErrorHandler(ErrorHandler):
    def handle_error(self, *, error_message, user, interface):
        Notification.send(
            kind=NotificationType.NotificationTypeChoices.SYSTEM,
            message=f"Validation for interface {interface.title} failed.",
            description=f"Validation for interface {interface.title} failed: {error_message}",
            actor=user,
        )
