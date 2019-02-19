from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage


@deconstructible
class S3Storage(S3Boto3Storage):
    """
    Wraps the s3 storage class but allows for configurable kwargs per
    backend. The upstream storage class is responsible for setting all
    of the kwargs.
    """

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **config, **kwargs)

        # If the attr was not set by the upstream, it's probably wrong
        if not all([hasattr(self, name) for name in config]):
            raise ImproperlyConfigured(
                f"Could not set all kwargs for S3 storage using {config}"
            )


private_s3_storage = S3Storage(config=settings.PRIVATE_S3_STORAGE_KWARGS)
protected_s3_storage = S3Storage(config=settings.PROTECTED_S3_STORAGE_KWARGS)
