import copy
import importlib

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

    for attr in ["access_key", "secret_key", "bucket_name", "endpoint_url"]:
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
