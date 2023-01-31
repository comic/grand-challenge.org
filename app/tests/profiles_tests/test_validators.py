import pytest
from django.core.exceptions import ValidationError

from grandchallenge.profiles.validators import username_is_not_email


def test_username_is_not_email():
    username_is_not_email("test")


def test_username_is_email_validator():
    with pytest.raises(ValidationError):
        username_is_not_email("test@gmail.com")
