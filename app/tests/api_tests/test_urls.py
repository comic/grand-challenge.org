import pytest

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
def test_api_docs_generation(
    client, schema, schema_format,
):
    kwargs = dict(format=schema_format) if schema == "schema-json" else None
    assert_viewname_status(
        code=200, url=reverse(f"api:{schema}", kwargs=kwargs), client=client,
    )
