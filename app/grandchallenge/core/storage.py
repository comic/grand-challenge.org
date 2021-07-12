import copy
import datetime
from base64 import b64decode
from uuid import uuid4

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.utils.text import get_valid_filename
from django.utils.timezone import now
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

    def copy(self, *, from_name, to_name):
        from_name = self._normalize_name(self._clean_name(from_name))
        to_name = self._normalize_name(self._clean_name(to_name))

        self.connection.meta.client.copy_object(
            Bucket=self.bucket_name,
            CopySource=f"{self.bucket_name}/{from_name}",
            Key=to_name,
        )


@deconstructible
class PrivateS3Storage(S3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, config=settings.PRIVATE_S3_STORAGE_KWARGS, **kwargs
        )

    def url(self, *args, **kwargs):
        """
        Urls for private storage should never be used, as S3Storage will
        generate a signed URL which will allow users to download the file.
        """
        raise NotImplementedError


@deconstructible
class ProtectedS3Storage(S3Storage):
    def __init__(self, *args, internal=False, **kwargs):
        config = copy.deepcopy(settings.PROTECTED_S3_STORAGE_KWARGS)

        # Setting a custom domain will strip the aws headers when using minio.
        # You can get these headers back by setting the custom_domain to None
        if internal:
            config["custom_domain"] = None

        super().__init__(*args, config=config, **kwargs)

    def cloudfront_signed_url(self, *, name, domain=None, expire=None):
        """
        Create a signed url that will be valid until the specific expiry date
        provided using a canned policy.

        Note: This grants the user permission to read the file.

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront.html#id57
        """
        name = self._normalize_name(self._clean_name(name))

        if domain is None:
            domain = settings.PROTECTED_S3_STORAGE_CLOUDFRONT_DOMAIN

        url = f"https://{domain}/{filepath_to_uri(name)}"

        if expire is None:
            expire = now() + datetime.timedelta(
                seconds=settings.CLOUDFRONT_URL_EXPIRY_SECONDS
            )

        return self._cloudfront_signer.generate_presigned_url(
            url, date_less_than=expire
        )

    @property
    def _cloudfront_signer(self):
        key_bytes = b64decode(
            settings.CLOUDFRONT_PRIVATE_KEY_BASE64.encode("ascii")
        )

        private_key = serialization.load_pem_private_key(
            key_bytes, password=None, backend=default_backend()
        )

        return CloudFrontSigner(
            settings.CLOUDFRONT_KEY_PAIR_ID,
            lambda m: private_key.sign(m, padding.PKCS1v15(), hashes.SHA1()),
        )


@deconstructible
class PublicS3Storage(S3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, config=settings.PUBLIC_S3_STORAGE_KWARGS, **kwargs
        )


private_s3_storage = PrivateS3Storage()
protected_s3_storage = ProtectedS3Storage()
internal_protected_s3_storage = ProtectedS3Storage(internal=True)
public_s3_storage = PublicS3Storage()

storages = [private_s3_storage, protected_s3_storage, public_s3_storage]

if len({s.bucket_name for s in storages}) != len(storages):
    raise ImproperlyConfigured("Storage bucket names are not unique")


def get_logo_path(instance, filename):
    return f"logos/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


def get_pdf_path(instance, filename):
    return f"pdfs/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


def get_social_image_path(instance, filename):
    return f"social-images/{instance.__class__.__name__.lower()}/{instance.pk}/{get_valid_filename(filename)}"


def get_banner_path(instance, filename):
    return f"b/{instance.pk}/{get_valid_filename(filename)}"


def get_mugshot_path(instance, filename):
    time_prefix = now().strftime("%Y/%m/%d")
    extension = filename.split(".")[-1].lower()
    return f"mugshots/{time_prefix}/{uuid4()}.{extension}"
