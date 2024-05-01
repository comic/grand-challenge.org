from importlib import import_module

from django.urls import URLPattern, URLResolver


def list_url_names(urlconf_name, pattern_names=None, prefix=""):  # noqa C901
    """Recursively collects all pattern names in a URL configuration into a set."""
    if pattern_names is None:
        pattern_names = set()

    # Import the URL configuration module dynamically
    try:
        urls = import_module(urlconf_name)
    except ImportError:
        # Handle cases where the URL configuration is not a module but an object
        urls = urlconf_name

    # Iterate through all URL patterns
    for pattern in urls.urlpatterns:
        if isinstance(pattern, URLPattern):
            # Add the pattern name if it exists
            if pattern.name:
                pattern_names.add(pattern.name)
        elif isinstance(pattern, URLResolver):
            # Recurse into included URL configurations
            if isinstance(pattern.urlconf_name, list) and all(
                isinstance(elem, URLPattern) for elem in pattern.urlconf_name
            ):
                for sub_pattern in pattern.urlconf_name:
                    if sub_pattern.name:
                        pattern_names.add(sub_pattern.name)
            else:
                pattern_names.update(
                    list_url_names(
                        pattern.urlconf_name.__name__,
                        pattern_names,
                        prefix + pattern.pattern.regex.pattern,
                    )
                )
        else:
            raise ValueError("Pattern is of unknown type")

    return pattern_names
