class ComponentBaseException(Exception):
    pass


class ComponentException(ComponentBaseException):
    """These exceptions will be sent to the user"""

    def __init__(self, message, message_details=None):
        super().__init__(message)
        self.message = message
        self.message_details = message_details


class RetryStep(ComponentBaseException):
    """Raised to signal that this step should be retried"""


class RetryTask(ComponentBaseException):
    """Raised if a new attempt should be made for this task"""


class TaskCancelled(ComponentBaseException):
    """Raised if a task has been cancelled"""


class UncleanExit(ComponentBaseException):
    """Raised if the process did not exit cleanly"""
