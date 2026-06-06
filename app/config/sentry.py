from subprocess import CalledProcessError

from botocore.exceptions import ClientError


def sentry_before_send(event, hint):
    """Mutate event/record extra fields based on exception type."""

    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
    elif "log_record" in hint:
        log_record = hint["log_record"]

        if log_record.exc_info:
            _, exc_value, _ = log_record.exc_info
        else:
            return event
    else:
        return event

    if isinstance(exc_value, CalledProcessError):
        extra = event.setdefault("extra", {})

        for attr in ("stderr", "stdout"):
            value = getattr(exc_value, attr)
            if isinstance(value, str):
                extra[attr] = value
            elif isinstance(value, bytes):
                extra[attr] = value.decode("utf-8", "replace")

    elif isinstance(exc_value, ClientError):
        extra = event.setdefault("extra", {})

        error = exc_value.response["Error"]
        extra["botocore_error_code"] = error["Code"]
        extra["botocore_error_message"] = error["Message"]

    return event
