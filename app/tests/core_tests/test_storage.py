import copy
import importlib
from datetime import datetime

import pytest
from django.conf import settings as dj_settings
from django.core.exceptions import ImproperlyConfigured

import grandchallenge.core.storage


def test_invalid_private_kwarg(settings):
    """Check that invalid kwargs raise a validation error."""
    settings.PRIVATE_S3_STORAGE_KWARGS["bogus_kwarg"] = "bogus"

    with pytest.raises(ImproperlyConfigured):
        importlib.reload(grandchallenge.core.storage)

    del settings.PRIVATE_S3_STORAGE_KWARGS["bogus_kwarg"]
    importlib.reload(grandchallenge.core.storage)


# Skip for now as settings unrolling does not work with a mutable setting
@pytest.mark.skip
def test_bucket_name_clash(settings):
    # Deep copy as otherwise you will modify the value in settings
    private_kwargs = copy.deepcopy(dj_settings.PRIVATE_S3_STORAGE_KWARGS)
    protected_kwargs = copy.deepcopy(dj_settings.PROTECTED_S3_STORAGE_KWARGS)

    private_kwargs["bucket_name"] = "foo"
    protected_kwargs["bucket_name"] = "foo"

    settings.PRIVATE_S3_STORAGE_KWARGS = private_kwargs
    settings.PROTECTED_S3_STORAGE_KWARGS = protected_kwargs

    with pytest.raises(ImproperlyConfigured):
        importlib.reload(grandchallenge.core.storage)

    # Revert to the original settings
    settings.PRIVATE_S3_STORAGE_KWARGS = dj_settings.PRIVATE_S3_STORAGE_KWARGS
    settings.PROTECTED_S3_STORAGE_KWARGS = (
        dj_settings.PROTECTED_S3_STORAGE_KWARGS
    )
    importlib.reload(grandchallenge.core.storage)


def test_s3_configs_differ():
    from grandchallenge.core.storage import (
        private_s3_storage,
        protected_s3_storage,
    )

    for attr in ["bucket_name", "endpoint_url"]:
        assert getattr(private_s3_storage, attr) != getattr(
            protected_s3_storage, attr
        )


def test_custom_domain():
    # By default we should get the custom domain in the url
    storage = grandchallenge.core.storage.ProtectedS3Storage()
    url = storage.url(name="foo")

    assert dj_settings.PROTECTED_S3_STORAGE_KWARGS["custom_domain"] in url
    assert dj_settings.PROTECTED_S3_STORAGE_KWARGS["endpoint_url"] not in url
    assert "AWSAccessKeyId" not in url

    # Turning off the custom domain should get us the internal endpoint url
    # with aws headers
    storage1 = grandchallenge.core.storage.ProtectedS3Storage(internal=True)
    url = storage1.url(name="foo")

    assert dj_settings.PROTECTED_S3_STORAGE_KWARGS["custom_domain"] not in url
    assert dj_settings.PROTECTED_S3_STORAGE_KWARGS["endpoint_url"] in url
    assert "AWSAccessKeyId" in url


def test_cloudfront_urls(settings):
    expected_url = (
        "https://d604721fxaaqy9.cloudfront.net/horizon.jpg?Expires=1258237200"
        "&Signature=Y70zPbq2rNoDXWLHJrdrx9KXgyXXrEQJY1i1EaBrIgPhyalCM5wPUegH6"
        "h4fn0FBysV85ZyXlS8CTM-yotLUd~HwXFJT-c3HgkZaACxQwaxetHMmFFUOdMVj-7qyp"
        "hMbI4wScfG4s-rV5pBBIKtNHZ6HV64Xnp6beqCFpUBcniQ_&Key-Pair-Id=PK123456"
        "789754"
    )

    settings.CLOUDFRONT_PRIVATE_KEY_BASE64 = (
        "LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlDWFFJQkFBS0JnUURBN2tp"
        "OWdJL2xSeWdJb09qVjF5eW1neDZGWUZsekorejFBVE1hTG81N25MNTdBYXZXCmhiNjhI"
        "WVk4RUEwR0pVOXhRZE1WYUhCb2dGM2VpQ1dZWFNVWkNXTS8rTTUrWmNkUXJhUlJTY3Vj"
        "bW42ZzRFdlkKMks0VzJweGJxSDh2bVVpa1B4aXI0MUVlQlBMak1Pekt2Ynp6UXk5ZS96"
        "eklRVlJFS1NwLzd5MW15d0lEQVFBQgpBb0dBQmM3bXA3WFlIeW51UFp4Q2hqV05KWklx"
        "K0E3M2dtMEFTRHY2QXQ3RjhWaTlyMHhVbFFlL3YwQVFTM3ljCk44UWx5UjRYTWJ6TUxZ"
        "azN5anhGRFhvNFpLUXRPR3pMR3RlQ1Uyc3JBTmlMdjI2L2ltWEE4RlZpZFpmdFRBdEwK"
        "dmlXUVpCVlBUZVlJQTY5QVRVWVBFcTBhNXU1d2pHeVVPaWo5T1d5dXkwMW1iUGtDUVFE"
        "bHVZb05wUE9la1EwWgpXclBnSjVyeGM4ZjZ6RzM3WlZvREJpZXhxdFZTaElGNVczeFl1"
        "V2hXNWtZYjBobGlZZmtxMTVjUzd0OW05NWgzCjFRSmYveEkvQWtFQTF2OWwvV04xYTFO"
        "M3JPSzRWR29Db2t4N2tSMlN5VE1TYlpnRjlJV0pOT3VnUi9XWnc3SFQKbmppcE8zYzlk"
        "eTFNczlwVUt3VUY0NmQ3MDQ5Y2s4SHdkUUpBUmdyU0t1TFdYTXlCSCsvbDFEeC9JNHRY"
        "dUFKSQpybFB5bytWbWlPYzdiNU56SHB0a1NIRVBmUjlzMU9LMFZxamtuY2xxQ0ozSWc4"
        "Nk9NRXRFRkJ6alpRSkJBS1l6CjQ3MGhjUGthR2s3dEtZQWdQNDhGdnhSc256ZW9vcHRV"
        "Ulc1RStNK1BRMlc5aURQUE9YOTczOStYaTAyaEdFV0YKQjBJR2JRb1RSRmRFNFZWY1BL"
        "MENRUUNlUzg0bE9EbEMwWTJCWnYySnhXM09zdi9Xa1VRNGRzbGZBUWwxVDMwMwo3dXd3"
        "cjdYVHJvTXY4ZElGUUlQcmVvUGhSS21kL1NiSnpiaUtmUy80UURoVQotLS0tLUVORCBS"
        "U0EgUFJJVkFURSBLRVktLS0tLQo="
    )
    settings.CLOUDFRONT_KEY_PAIR_ID = "PK123456789754"

    storage = grandchallenge.core.storage.ProtectedS3Storage()

    signed_url = storage.cloudfront_signed_url(
        name="horizon.jpg",
        domain="d604721fxaaqy9.cloudfront.net",
        expire=datetime.utcfromtimestamp(1258237200),
    )

    assert signed_url == expected_url


def test_private_storage_url_generation_fails():
    storage = grandchallenge.core.storage.PrivateS3Storage()

    with pytest.raises(NotImplementedError):
        storage.url(name="test.jpg")
