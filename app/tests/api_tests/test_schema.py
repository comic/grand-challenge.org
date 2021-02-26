from drf_spectacular.validation import validate_schema

from grandchallenge.api.urls import SchemaView


def test_schema_is_valid():
    schema_view = SchemaView()

    generator = schema_view.generator_class(
        urlconf=schema_view.urlconf, api_version=schema_view.api_version
    )
    schema = generator.get_schema(request=None, public=True)

    validate_schema(schema)

    # TODO: fix the warnings from types that could not be inferred
    # from drf_spectacular.drainage import GENERATOR_STATS
    # assert not GENERATOR_STATS
