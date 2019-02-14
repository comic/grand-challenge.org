from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import get_storage_class
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDefaultStorage(
    get_storage_class(settings.PRIVATE_DEFAULT_STORAGE)
):
    """
    Wraps a storage class but allows for configurable kwargs per storage
    backend. The upstream storage class is responsible for setting all
    of the kwargs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, **kwargs, **settings.PRIVATE_DEFAULT_STORAGE_KWARGS
        )

        # If the attr was not set by the upstream, it's probably wrong
        if not all(
            [
                hasattr(self, name)
                for name in settings.PRIVATE_DEFAULT_STORAGE_KWARGS
            ]
        ):
            raise ImproperlyConfigured(
                "Not all of the PRIVATE_DEFAULT_STORAGE_KWARGS could be set"
                f"for {settings.PRIVATE_DEFAULT_STORAGE}."
            )


private_default_storage = PrivateDefaultStorage()
