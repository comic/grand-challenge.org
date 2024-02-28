import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


class HexColorField(models.CharField):
    default_validators = [
        RegexValidator(
            regex=r"^#[a-fA-F0-9]{6}$",
            message="This is an invalid color code. It must be an HTML hexadecimal color code e.g. #000000",
        )
    ]

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 7
        super().__init__(*args, **kwargs)


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
