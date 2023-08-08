import re
from collections.abc import Hashable
from pathlib import Path

import magic
import referencing
import referencing.retrieval
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from jsonschema import SchemaError
from jsonschema import ValidationError as JSONValidationError
from jsonschema import validate, validators


@deconstructible
class MimeTypeValidator:
    allowed_types = ()

    def __init__(self, *, allowed_types: tuple[str, ...]):
        self.allowed_types = tuple(x.lower() for x in allowed_types)
        super().__init__()

    def __call__(self, value):
        if isinstance(value, list):
            for v in value:
                self._validate_mimetype(v)
        else:
            self._validate_mimetype(value)

    def _validate_mimetype(self, value):
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
class ExtensionValidator:
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

    def __init__(self, *, allowed_extensions: tuple[str, ...]):
        self.allowed_extensions = tuple(x.lower() for x in allowed_extensions)
        super().__init__()

    def __call__(self, value):
        if isinstance(value, list):
            for v in value:
                self._validate_filepath(v.name)
        else:
            self._validate_filepath(value.name)

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


def get_file_mimetype(file):
    n_bytes = 2048

    try:
        file.seek(0)
        mimetype = magic.from_buffer(file.read(n_bytes), mime=True)
        file.seek(0)
    except AttributeError:
        # File not open, so manage that here
        with file.open("rb") as f:
            mimetype = magic.from_buffer(f.read(n_bytes), mime=True)

    return mimetype


class JSONSchemaRegistry:
    """
    Registry for cached retrieval of external JSON-schema references.

    A set of allowed regexes can be provided: these will limit which
    URIs are allowed to be retrieved.

    Each set of regexes will result in a singleton registry with its own cache.
    """

    _instances = {}

    def __new__(
        cls, *, allowed_regexes=settings.ALLOWED_JSON_SCHEMA_REF_REGEXES
    ):
        lookup_key = cls._get_instance_lookup_key(allowed_regexes)
        instance = cls._instances.get(lookup_key)
        if instance is None:
            retrieve_func = cls._limited_retrieve(
                allowed_regexes, retrieve=cls._retrieve_via_requests
            )
            instance = referencing.Registry(retrieve=retrieve_func)
            cls._instances[lookup_key] = instance
        return instance

    @staticmethod
    def _get_instance_lookup_key(regexes):
        """Returns a hash that identifies an allow list"""
        for regex in regexes:  # Sanity checks
            assert isinstance(regex, Hashable)
            re.compile(regex)
        # deduplicate
        regexes = list(set(regexes))
        # ensure order
        regexes.sort()
        return hash(tuple(regexes))

    @staticmethod
    @referencing.retrieval.to_cached_resource()
    def _retrieve_via_requests(uri):
        return requests.get(uri).text

    @staticmethod
    def _limited_retrieve(allowed_regexes, retrieve):
        def wrapper(uri):
            for regex in allowed_regexes:
                if re.match(regex, uri):
                    return retrieve(uri)
            raise referencing.exceptions.NoSuchResource(uri)

        return wrapper


@deconstructible
class JSONValidator:
    """Uses jsonschema to validate json fields."""

    schema = None

    def __init__(self, *, schema: dict):
        self.schema = schema
        super().__init__()

    def __call__(self, value):
        try:
            validate(value, self.schema, registry=JSONSchemaRegistry())
        except JSONValidationError as e:
            raise ValidationError(f"JSON does not fulfill schema: {e}")

    def __eq__(self, other):
        return isinstance(other, JSONValidator) and self.schema == other.schema

    def __ne__(self, other):
        return not (self == other)


@deconstructible
class JSONSchemaValidator:
    """Validates JSON Schema against the latest or defined schema."""

    def __call__(self, value):
        try:
            cls = validators.validator_for(schema=value)
            cls.check_schema(schema=value)
        except SchemaError as e:
            raise ValidationError(f"Invalid schema: {e}")

    def __eq__(self, other):
        return isinstance(other, JSONValidator)

    def __ne__(self, other):
        return not (self == other)
