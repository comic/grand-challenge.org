from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.core.fields import RegexField


@pytest.mark.parametrize(
    "value, error",
    (
        (
            r"[abc]",
            nullcontext(),
        ),
        (
            r"[abc",  # Missing closing bracket
            pytest.raises(ValidationError),
        ),
    ),
)
def test_regex_field_validation(value, error):
    with error:
        RegexField._validate_regex(value)
