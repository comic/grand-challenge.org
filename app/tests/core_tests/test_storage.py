import copy
import importlib
from datetime import datetime
from textwrap import dedent

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


def test_cloudfront_urls(settings, tmpdir):
    pem = tmpdir.join("cf.pem")
    pem.write(
        dedent(
            """
            -----BEGIN RSA PRIVATE KEY-----
            MIICXQIBAAKBgQDA7ki9gI/lRygIoOjV1yymgx6FYFlzJ+z1ATMaLo57nL57AavW
            hb68HYY8EA0GJU9xQdMVaHBogF3eiCWYXSUZCWM/+M5+ZcdQraRRScucmn6g4EvY
            2K4W2pxbqH8vmUikPxir41EeBPLjMOzKvbzzQy9e/zzIQVREKSp/7y1mywIDAQAB
            AoGABc7mp7XYHynuPZxChjWNJZIq+A73gm0ASDv6At7F8Vi9r0xUlQe/v0AQS3yc
            N8QlyR4XMbzMLYk3yjxFDXo4ZKQtOGzLGteCU2srANiLv26/imXA8FVidZftTAtL
            viWQZBVPTeYIA69ATUYPEq0a5u5wjGyUOij9OWyuy01mbPkCQQDluYoNpPOekQ0Z
            WrPgJ5rxc8f6zG37ZVoDBiexqtVShIF5W3xYuWhW5kYb0hliYfkq15cS7t9m95h3
            1QJf/xI/AkEA1v9l/WN1a1N3rOK4VGoCokx7kR2SyTMSbZgF9IWJNOugR/WZw7HT
            njipO3c9dy1Ms9pUKwUF46d7049ck8HwdQJARgrSKuLWXMyBH+/l1Dx/I4tXuAJI
            rlPyo+VmiOc7b5NzHptkSHEPfR9s1OK0VqjknclqCJ3Ig86OMEtEFBzjZQJBAKYz
            470hcPkaGk7tKYAgP48FvxRsnzeooptURW5E+M+PQ2W9iDPPOX9739+Xi02hGEWF
            B0IGbQoTRFdE4VVcPK0CQQCeS84lODlC0Y2BZv2JxW3Osv/WkUQ4dslfAQl1T303
            7uwwr7XTroMv8dIFQIPreoPhRKmd/SbJzbiKfS/4QDhU
            -----END RSA PRIVATE KEY-----
            """
        )
    )

    expected_url = "https://d604721fxaaqy9.cloudfront.net/horizon.jpg?Expires=1258237200&Signature=Y70zPbq2rNoDXWLHJrdrx9KXgyXXrEQJY1i1EaBrIgPhyalCM5wPUegH6h4fn0FBysV85ZyXlS8CTM-yotLUd~HwXFJT-c3HgkZaACxQwaxetHMmFFUOdMVj-7qyphMbI4wScfG4s-rV5pBBIKtNHZ6HV64Xnp6beqCFpUBcniQ_&Key-Pair-Id=PK123456789754"

    settings.CLOUDFRONT_PRIVATE_KEY_PATH = pem.strpath
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
