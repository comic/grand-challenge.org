class ComponentBaseException(Exception):
    pass


class ComponentException(ComponentBaseException):
    """These exceptions will be sent to the user"""


class RetryStep(ComponentBaseException):
    """Raised to signal that this step should be retried"""


class TaskCancelled(ComponentBaseException):
    """Raised if a task has been cancelled"""
