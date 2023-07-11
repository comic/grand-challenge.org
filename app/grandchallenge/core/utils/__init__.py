from distutils.util import strtobool as strtobool_i
from functools import wraps


def disable_for_loaddata(signal_handler):
    """Decorator for disabling a signal handler when using manage.py loaddata."""

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs["raw"]:
            print(f"Skipping signal for {args} {kwargs}")
            return

        signal_handler(*args, **kwargs)

    return wrapper


def strtobool(val) -> bool:
    """Return disutils.util.strtobool as a boolean."""
    return bool(strtobool_i(val))
