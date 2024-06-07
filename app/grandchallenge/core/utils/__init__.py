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
    val = val.lower()
    if val in {"y", "yes", "t", "true", "on", "1"}:
        return True
    elif val in {"n", "no", "f", "false", "off", "0"}:
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")
