class ComponentBaseException(Exception):
    pass


class ComponentException(ComponentBaseException):
    """These exceptions will be sent to the user"""

    pass


class RetryStep(ComponentBaseException):
    """Raised to signal that this step should be retried"""

    pass
