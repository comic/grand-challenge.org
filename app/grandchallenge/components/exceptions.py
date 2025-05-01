class PriorStepFailed(Exception):
    """Raised when a dependent step has failed"""


class InstanceInUse(Exception):
    """Raised when a container image is in use"""
