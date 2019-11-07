from pathlib import Path
from typing import Tuple

import magic
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from jsonschema import ValidationError as JSONValidationError, validate


@deconstructible
class MimeTypeValidator(object):
    allowed_types = ()

    def __init__(self, *, allowed_types: Tuple[str, ...]):
        self.allowed_types = tuple(x.lower() for x in allowed_types)
        super().__init__()

    def __call__(self, value):
        mimetype = get_file_mimetype(value)
        if mimetype.lower() not in self.allowed_types:
            raise ValidationError(
                f"File of type {mimetype} is not supported. "
                "Allowed types are "
                f'{", ".join(self.allowed_types)}.'
            )

    def __eq__(self, other):
        return isinstance(other, MimeTypeValidator) and set(
            self.allowed_types
        ) == set(other.allowed_types)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(MimeTypeValidator) + 7 * hash(self.allowed_types)


@deconstructible
class ExtensionValidator(object):
    """
    Performs soft validation of the filename. Usage:

        validators=[
            ExtensionValidator(
                allowed_extensions=(
                    '.tar',
                    )
                ),
            ],

    """

    allowed_extensions = ()

    def __init__(self, *, allowed_extensions: Tuple[str, ...]):
        self.allowed_extensions = tuple(x.lower() for x in allowed_extensions)
        super().__init__()

    def __call__(self, value):
        try:
            self._validate_filepath(value.name)
        except AttributeError:
            # probably passed a list
            for v in value:
                self._validate_filepath(v.name)

    def _validate_filepath(self, s):
        extensions = Path(s).suffixes
        extension = "".join(extensions).lower()

        if not any(extension.endswith(e) for e in self.allowed_extensions):
            raise ValidationError(
                f"File of type {extension} is not supported."
                " Allowed types are "
                f'{", ".join(self.allowed_extensions)}.'
            )

    def __eq__(self, other):
        return isinstance(other, ExtensionValidator) and set(
            self.allowed_extensions
        ) == set(other.allowed_extensions)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(ExtensionValidator) + 7 * hash(self.allowed_extensions)


def get_file_mimetype(f):
    mimetype = magic.from_buffer(f.read(1024), mime=True)
    f.seek(0)
    return mimetype


@deconstructible
class JSONSchemaValidator(object):
    """Uses jsonschema to validate json fields."""

    schema = None

    def __init__(self, *, schema: dict):
        self.schema = schema
        super().__init__()

    def __call__(self, value):
        try:
            validate(value, self.schema)
        except JSONValidationError as e:
            raise ValidationError(str(e))

    def __eq__(self, other):
        return (
            isinstance(other, JSONSchemaValidator)
            and self.schema == other.schema
        )

    def __ne__(self, other):
        return not (self == other)
