from typing import Dict

from django.db.models import CharField
from drf_yasg.inspectors import FieldInspector
from drf_yasg.openapi import Schema


def _add_manual_fields(_, serializer_or_field, schema):
    meta = getattr(serializer_or_field, "Meta", None)
    swagger_schema_fields = getattr(meta, "swagger_schema_fields", {})
    if swagger_schema_fields:
        _update_swagger_schema_fields(schema, swagger_schema_fields)


def _update_swagger_schema_fields(schema, swagger_schema_fields):
    for attr, val in swagger_schema_fields.items():
        if isinstance(val, dict) and isinstance(
            getattr(schema, attr, None), dict
        ):
            to_update = dict(
                list(getattr(schema, attr).items()) + list(val.items())
            )
            setattr(schema, attr, to_update)
        else:
            setattr(schema, attr, val)


# This overrides the default behavior when the swagger_schema_fields attribute is set
# in the serializers. Now dictionary attributes are updated instead of overwritten
# for the swagger_schema_fields - Sil
FieldInspector.add_manual_fields = _add_manual_fields


def swagger_schema_fields_for_charfield(
    *_, **kwargs: CharField
) -> Dict[str, Dict[str, Schema]]:
    return {
        "properties": {
            char_field_name: Schema(
                **{
                    "enum": [c[1] for c in char_field.choices],
                    "title": char_field_name[0].upper()
                    + char_field_name[1:].replace("_", " "),
                    "type": "string",
                    "minLength": 1,
                }
            )
            for char_field_name, char_field in kwargs.items()
        }
    }
