from subprocess import CalledProcessError

from botocore.exceptions import ClientError


def sentry_before_send(event, hint):
    """Add stderr to the event if the exception is a CalledProcessError"""
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        if isinstance(exc_value, CalledProcessError) and hasattr(
            exc_value, "stderr"
        ):
            event["extra"] = event.get("extra", {})

            if isinstance(exc_value.stderr, str):
                event["extra"]["stderr"] = exc_value.stderr
            elif isinstance(exc_value.stderr, bytes):
                event["extra"]["stderr"] = exc_value.stderr.decode(
                    "utf-8", "replace"
                )
            else:
                # Do not include stderr
                pass
        elif isinstance(exc_value, ClientError):
            event["extra"] = event.get("extra", {})

            error = exc_value.response["Error"]
            event["extra"]["botocore_error_code"] = error["Code"]
            event["extra"]["botocore_error_message"] = error["Message"]

    return event
