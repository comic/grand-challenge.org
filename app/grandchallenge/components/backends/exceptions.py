class ComponentBaseException(Exception):
    pass


class ComponentException(ComponentBaseException):
    """These exceptions will be sent to the user."""


class RetryStep(ComponentBaseException):
    """Raised to signal that this step should be retried."""


class RetryTask(ComponentBaseException):
    """Raised if a new attempt should be made for this task."""


class TaskCancelled(ComponentBaseException):
    """Raised if a task has been cancelled."""
