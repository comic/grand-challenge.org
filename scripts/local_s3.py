import json
import logging
from uuid import uuid4

import boto3
import botocore
from django.conf import settings

logger = logging.getLogger(__name__)


def run():
    """Sets up the permissions on the s3 buckets"""
    logger.info("🔐 Setting up local s3 🔐")

    if not settings.DEBUG:
        raise RuntimeError("Server is not in DEBUG mode.")

    if not settings.AWS_S3_ENDPOINT_URL:
        raise RuntimeError("This should only be run against local s3")

    client = boto3.client(
        "s3",
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    )

    _create_buckets(client=client)
    _set_public_bucket_policy(client=client)

    logger.info("✨ Local s3 set up ✨")


def _create_buckets(*, client):
    bucket_names = [
        settings.PRIVATE_S3_STORAGE_KWARGS["bucket_name"],
        settings.PROTECTED_S3_STORAGE_KWARGS["bucket_name"],
        settings.PUBLIC_S3_STORAGE_KWARGS["bucket_name"],
        settings.UPLOADS_S3_BUCKET_NAME,
        settings.COMPONENTS_INPUT_BUCKET_NAME,
        settings.COMPONENTS_OUTPUT_BUCKET_NAME,
    ]

    for bucket_name in bucket_names:
        try:
            client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created {bucket_name}")
        except botocore.exceptions.ClientError as error:
            if error.response["Error"]["Code"] in {
                "BucketAlreadyExists",
                "BucketAlreadyOwnedByYou",
            }:
                logger.info(f"{bucket_name} already exists, skipping creation")
            else:
                raise

        # Interact with the bucket to ensure that it is set up
        test_uuid = uuid4().bytes
        test_key = "local_s3_setup"

        try:
            client.put_object(Bucket=bucket_name, Key=test_key, Body=test_uuid)
            response = client.get_object(Bucket=bucket_name, Key=test_key)

            if response["Body"].read() == test_uuid:
                logger.info(f"{bucket_name} is writable")
            else:
                raise RuntimeError(
                    f"Test objects do not match in {bucket_name}"
                )
        finally:
            client.delete_object(Bucket=bucket_name, Key=test_key)


def _set_public_bucket_policy(*, client):
    public_bucket_name = settings.PUBLIC_S3_STORAGE_KWARGS["bucket_name"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{public_bucket_name}/*",
            }
        ],
    }

    client.put_bucket_policy(
        Bucket=public_bucket_name, Policy=json.dumps(policy)
    )
