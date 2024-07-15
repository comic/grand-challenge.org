class PathResolutionException(Exception):
    """
    Raised when a path given to a template tag contained variables that could
    not be resolved.
    """


class LockNotAcquiredException(Exception):
    """Raised when a lock could not be acquired."""
