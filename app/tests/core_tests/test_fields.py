from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db import models

from grandchallenge.core.fields import RegexField


class ModelWithRegex(models.Model):
    regex = RegexField()


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
    model = ModelWithRegex(regex=value)
    with error:
        model.full_clean()
