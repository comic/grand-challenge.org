import re
from functools import wraps

from django.conf import settings


def build_absolute_uri(request):
    """
    Total hack to get around SUBDOMAN_IS_PROJECTNAME for absolute urls
    TODO: This might no longer be needed
    """
    subdomain_absolute_uri = request.build_absolute_uri()
    if settings.SUBDOMAIN_IS_PROJECTNAME:
        try:
            m = re.search(
                r"\/\/(?P<host>[^\/]+)\/site\/(?P<subdomain>[^\/]+)\/",
                subdomain_absolute_uri + "/",
            )
            host = m["host"]
            subdomain = m["subdomain"]
            subdomain_absolute_uri = (
                subdomain_absolute_uri[: m.start(0)]
                + "//"
                + subdomain
                + "."
                + host
                + "/"
                + subdomain_absolute_uri[m.end(0) :]
            )
        except TypeError:
            # nothing to rewrite
            pass
    return subdomain_absolute_uri


def disable_for_loaddata(signal_handler):
    """Decorator for disabling a signal handler when using loaddata"""

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs["raw"]:
            print(f"Skipping signal for {args} {kwargs}")
            return

        signal_handler(*args, **kwargs)

    return wrapper
