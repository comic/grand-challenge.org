import importlib
import inspect
from typing import Dict, Type

import pytest
import rest_framework.fields
from django.db.models import CharField
from rest_framework.serializers import ModelSerializer

import grandchallenge.api.urls
from grandchallenge.reader_studies.models import ANSWER_TYPE_SCHEMA
from grandchallenge.reader_studies.serializers import QuestionSerializer
from grandchallenge.subdomains.utils import reverse
from tests.utils import assert_viewname_status


@pytest.mark.parametrize(
    "schema, schema_format",
    [
        ("schema-json", ".json"),
        ("schema-json", ".yaml"),
        ("schema-docs", None),
    ],
)
@pytest.mark.django_db
def test_api_docs_generation(client, schema, schema_format):
    kwargs = dict(format=schema_format) if schema == "schema-json" else None
    response = assert_viewname_status(
        code=200, url=reverse(f"api:{schema}", kwargs=kwargs), client=client
    )
    if schema_format is not None:
        assert len(response.data["paths"]) > 0
        check_answer_type_schema_from_response(response)
        check_response_schema_formatting(response)
    else:
        assert len(response.content) > 0


def check_answer_type_schema_from_response(response):
    schema = response.data["definitions"]["Answer"]["properties"]["answer"]
    assert {"title": "Answer", **ANSWER_TYPE_SCHEMA} == schema


def check_response_schema_formatting(response):
    definitions = response.data["definitions"]
    serializers = extract_all_api_exposed_model_serializers()
    for serializer in serializers:
        if hasattr(serializer, "Meta") and hasattr(serializer.Meta, "model"):
            model_name = serializer.Meta.model.__name__
            if model_name not in (
                "ImagingModality",
                "Patient",
                "Study",
                "Archive",
            ):
                assert model_name in definitions
                check_serializer_charfield_schema_formatting(
                    definitions=definitions, serializer=serializer
                )


def extract_all_api_exposed_model_serializers():
    serializer_module_names = {
        klass.__module__.replace(".views", ".serializers")
        for _, klass, _ in grandchallenge.api.urls.router.registry
    }
    serializers = []
    for module_name in serializer_module_names:
        module = importlib.import_module(module_name)
        serializers = serializers + [
            v
            for v in module.__dict__.values()
            if inspect.isclass(v) and issubclass(v, (ModelSerializer,))
        ]
    return serializers


def check_serializer_charfield_schema_formatting(
    *, definitions: Dict, serializer: Type[ModelSerializer]
):
    model = serializer.Meta.model
    model_field_names = [f.name for f in model._meta.fields]
    model_property_definitions = definitions[model.__name__]["properties"]
    name_remapping = (
        {"form_direction": "direction"} if model is QuestionSerializer else {}
    )
    char_field_names = [
        field_name
        for field_name, field in serializer._declared_fields.items()
        if isinstance(field, rest_framework.fields.CharField)
    ]
    for field_name in char_field_names:
        if field_name in model_field_names:
            field_name = (
                field_name
                if field_name not in name_remapping
                else name_remapping[field_name]
            )
            char_field = model._meta.get_field(field_name)
            if (
                isinstance(char_field, CharField)
                and len(char_field.choices) > 0
            ):
                check_charfield_schema_formatting(
                    definitions=model_property_definitions,
                    char_field=char_field,
                )


def check_charfield_schema_formatting(
    *, definitions: Dict, char_field: CharField
):
    name = char_field.name
    assert name in definitions
    schema = definitions[name]
    assert schema["type"] == "string"
    assert schema["minLength"] == 1
    assert schema["title"] == name[0].upper() + name[1:].replace("_", " ")
    assert "enum" in schema
    assert schema["enum"] == [e[1] for e in char_field.choices]
