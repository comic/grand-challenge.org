from distutils.util import strtobool as strtobool_i
from functools import wraps

from django.http import HttpResponse


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


def htmx_refresh(handler):
    """
    Decorator that adds a HX-refresh header if the returned HTTPResponse
    of the provided handler is successful
    """

    @wraps(handler)
    def wrapper(*args, **kwargs):
        response = handler(*args, **kwargs)
        if response is None:
            response = HttpResponse()
        if 200 <= response.status_code < 300:
            response["HX-Refresh"] = "true"
        return response

    return wrapper
