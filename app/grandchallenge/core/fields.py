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
