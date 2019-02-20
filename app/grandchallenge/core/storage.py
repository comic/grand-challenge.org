import copy

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible
from storages.backends.s3boto3 import S3Boto3Storage


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


@deconstructible
class PrivateS3Storage(S3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, config=settings.PRIVATE_S3_STORAGE_KWARGS, **kwargs
        )


@deconstructible
class ProtectedS3Storage(S3Storage):
    def __init__(self, *args, internal=False, **kwargs):
        config = copy.deepcopy(settings.PROTECTED_S3_STORAGE_KWARGS)

        # Setting a custom domain will strip the aws headers when using minio.
        # You can get these headers back by setting the custom_domain to None
        if internal:
            config["custom_domain"] = None

        super().__init__(*args, config=config, **kwargs)


private_s3_storage = PrivateS3Storage()
protected_s3_storage = ProtectedS3Storage()

if protected_s3_storage.bucket_name == private_s3_storage.bucket_name:
    raise ImproperlyConfigured(
        "Private and Protected storage point to the same bucket"
    )
