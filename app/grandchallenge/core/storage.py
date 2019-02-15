from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage


@deconstructible
class PrivateS3Storage(S3Boto3Storage):
    """
    Wraps the s3 storage class but allows for configurable kwargs per
    backend. The upstream storage class is responsible for setting all
    of the kwargs.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, **settings.PRIVATE_S3_STORAGE_KWARGS)

        # If the attr was not set by the upstream, it's probably wrong
        if not all(
            [
                hasattr(self, name)
                for name in settings.PRIVATE_S3_STORAGE_KWARGS
            ]
        ):
            raise ImproperlyConfigured(
                "Not all of the PRIVATE_S3_STORAGE_KWARGS could be set"
            )


private_s3_storage = PrivateS3Storage()
