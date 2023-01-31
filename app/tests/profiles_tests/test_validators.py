from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.profiles.validators import username_is_not_email


@pytest.mark.parametrize(
    "test_input,expectation",
    [
        ("test", nullcontext()),
        ("test@gmail.com", pytest.raises(ValidationError)),
    ],
)
def test_username_validation(test_input, expectation):
    with expectation:
        username_is_not_email(test_input)
