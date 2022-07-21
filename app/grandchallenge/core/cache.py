def _cache_key_from_method(method):
    return f"lock.{method.__module__}.{method.__name__}"
