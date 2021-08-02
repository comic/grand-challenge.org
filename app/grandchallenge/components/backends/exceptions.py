class ComponentException(Exception):
    """These exceptions will be sent to the user"""


class ComponentJobActive(Exception):
    """Raised if a job is still active"""
