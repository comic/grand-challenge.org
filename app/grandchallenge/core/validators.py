import re
from functools import cache
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

from grandchallenge.components import models as components_models


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


class JSONSchemaRetrieve:
    """
    A cached retrieve that can be used in referencing.Registry.

    The URIs retrieved are limited to those that match the allowed_regexes.
    """

    def __init__(self, *, allowed_regexes):
        self.allowed_regexes = allowed_regexes

    @staticmethod
    @referencing.retrieval.to_cached_resource()
    def _retrieve_via_requests(uri):
        return requests.get(uri).text

    def __call__(self, uri):
        for regex in self.allowed_regexes:
            if re.match(regex, uri):
                return self._retrieve_via_requests(uri)
        raise referencing.exceptions.NoSuchResource(uri)


@cache
def get_json_schema_registry():
    retrieve = JSONSchemaRetrieve(
        allowed_regexes=settings.ALLOWED_JSON_SCHEMA_REF_SRC_REGEXES,
    )
    return referencing.Registry(retrieve=retrieve)


@deconstructible
class JSONValidator:
    """Uses jsonschema to validate json fields."""

    schema = None

    def __init__(self, *, schema: dict):
        self.schema = schema
        self.registry = get_json_schema_registry()
        super().__init__()

    def __call__(self, value):
        try:
            validate(value, self.schema, registry=self.registry)
        except JSONValidationError as e:
            raise ValidationError(
                f"JSON does not fulfill schema: instance {e.message.replace(str(e.instance) + ' ', '')}"
            )

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


@deconstructible
class ViewContentValidator:
    """Validates view_content JSON against governing rules."""

    def __call__(self, value):
        if not hasattr(value, "items"):
            raise ValidationError("View content is invalid")

        for viewport, slugs in value.items():
            viewport_interfaces = (
                components_models.ComponentInterface.objects.filter(
                    slug__in=slugs
                )
            )

            if set(slugs) != {i.slug for i in viewport_interfaces}:
                raise ValidationError(
                    f"Unknown interfaces in view content for viewport {viewport}: {', '.join(slugs)}"
                )

            image_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind
                == components_models.InterfaceKind.InterfaceKindChoices.IMAGE
            ]

            if len(image_interfaces) > 1:
                raise ValidationError(
                    "Maximum of one image interface is allowed per viewport, "
                    f"got {len(image_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in image_interfaces)}"
                )

            mandatory_isolation_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind
                in components_models.InterfaceKind.interface_type_mandatory_isolation()
            ]

            if len(mandatory_isolation_interfaces) > 1 or (
                len(mandatory_isolation_interfaces) == 1
                and len(viewport_interfaces) > 1
            ):
                raise ValidationError(
                    "Some of the selected interfaces can only be displayed in isolation, "
                    f"found {len(mandatory_isolation_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in mandatory_isolation_interfaces)}"
                )

            undisplayable_interfaces = [
                i
                for i in viewport_interfaces
                if i.kind
                in components_models.InterfaceKind.interface_type_undisplayable()
            ]

            if len(undisplayable_interfaces) > 0:
                raise ValidationError(
                    "Some of the selected interfaces cannot be displayed, "
                    f"found {len(undisplayable_interfaces)} for viewport {viewport}: "
                    f"{', '.join(i.slug for i in undisplayable_interfaces)}"
                )

    def __eq__(self, other):
        return isinstance(other, ViewContentValidator)
