import logging
from subprocess import CalledProcessError

logger = logging.getLogger(__name__)


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

            logger.warning(
                f"Subprocess stderr: {event["extra"].get("stderr")}"
            )

    return event
