import pytest
from drf_spectacular.validation import validate_schema
from drf_spectacular.views import SpectacularAPIView


@pytest.mark.django_db
def test_schema_is_valid(settings):
    settings.ROOT_URLCONF = "config.urls.root"

    schema_view = SpectacularAPIView()

    generator = schema_view.generator_class(
        urlconf=schema_view.urlconf, api_version=schema_view.api_version
    )
    schema = generator.get_schema(
        request=None, public=schema_view.serve_public
    )

    validate_schema(schema)

    from drf_spectacular.drainage import GENERATOR_STATS

    assert not GENERATOR_STATS
