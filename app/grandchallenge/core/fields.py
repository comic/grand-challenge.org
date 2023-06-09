import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class HexColorField(models.CharField):
    def __init__(self, **kwargs):
        validators = kwargs.pop("validators", [])
        validators.append(
            RegexValidator(
                regex=r"^#[a-fA-F0-9]{6}$",
                message="This is an invalid color code. It must be an HTML hexadecimal color code e.g. #000000",
            )
        )
        kwargs["validators"] = validators
        kwargs["max_length"] = 7
        super().__init__(
            **kwargs,
        )


class RegexField(models.TextField):
    description = "A regular expression"

    @staticmethod
    def _validate_regex(value):
        try:
            re.compile(value)
        except re.error:
            raise ValidationError("Invalid regular expression")

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        self._validate_regex(value)
        return value
