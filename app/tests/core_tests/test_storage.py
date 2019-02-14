import importlib

import pytest
from django.core.exceptions import ImproperlyConfigured

import grandchallenge.core.storage


def test_invalid_private_kwarg(settings):
    """
    Checks that invalid kwargs raise a validation error
    """
    settings.PRIVATE_S3_STORAGE_KWARGS["bogus_kwarg"] = "bogus"

    with pytest.raises(ImproperlyConfigured):
        importlib.reload(grandchallenge.core.storage)

    del settings.PRIVATE_S3_STORAGE_KWARGS["bogus_kwarg"]
    importlib.reload(grandchallenge.core.storage)
