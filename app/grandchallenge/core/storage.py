import copy
import json

import boto3
from botocore.exceptions import NoCredentialsError
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


@deconstructible
class PublicS3Storage(S3Storage):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, config=settings.PUBLIC_S3_STORAGE_KWARGS, **kwargs
        )


private_s3_storage = PrivateS3Storage()
protected_s3_storage = ProtectedS3Storage()
public_s3_storage = PublicS3Storage()

storages = [private_s3_storage, protected_s3_storage, public_s3_storage]

if len({s.bucket_name for s in storages}) != len(storages):
    raise ImproperlyConfigured("Storage bucket names are not unique")

if settings.DEBUG:

    def setup_public_storage():
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetBucketLocation",
                    "Resource": f"arn:aws:s3:::{public_s3_storage.bucket_name}",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{public_s3_storage.bucket_name}",
                },
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{public_s3_storage.bucket_name}/*",
                },
            ],
        }
        bucket_policy = json.dumps(bucket_policy)

        # Get or create the bucket
        try:
            _ = public_s3_storage.bucket
        except NoCredentialsError:
            return

        s3 = boto3.client(
            "s3",
            aws_access_key_id=public_s3_storage.access_key,
            aws_secret_access_key=public_s3_storage.secret_key,
            aws_session_token=public_s3_storage.security_token,
            region_name=public_s3_storage.region_name,
            use_ssl=public_s3_storage.use_ssl,
            endpoint_url=public_s3_storage.endpoint_url,
            config=public_s3_storage.config,
            verify=public_s3_storage.verify,
        )

        try:
            s3.put_bucket_policy(
                Bucket=public_s3_storage.bucket_name, Policy=bucket_policy
            )
        except NoCredentialsError:
            pass

    setup_public_storage()
