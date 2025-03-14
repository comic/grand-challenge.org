import pytest
from django.conf import settings

from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.subdomains.utils import reverse
from tests.utils import assert_viewname_status


@pytest.mark.xfail
@pytest.mark.parametrize(
    "schema, content_type",
    [
        ("schema", "application/vnd.oai.openapi+json"),
        ("schema", "application/vnd.oai.openapi"),
    ],
)
@pytest.mark.django_db
def test_api_docs_generation(client, schema, content_type):
    response = assert_viewname_status(
        code=200,
        url=reverse(f"api:{schema}"),
        client=client,
        HTTP_ACCEPT=content_type,
    )
    assert len(response.data["paths"]) > 0
    check_answer_type_schema_from_response(response)


def check_answer_type_schema_from_response(response):
    schema = response.data["definitions"]["Answer"]["properties"]["answer"]
    assert {"title": "Answer", **ANSWER_TYPE_SCHEMA} == schema


@pytest.mark.django_db
def test_api_lowest_gcapi_version_check(client):
    response = assert_viewname_status(
        code=200,
        url=reverse("api:gcapi"),
        client=client,
    )
    assert response.data["latest_version"] == settings.GCAPI_LATEST_VERSION
    assert (
        response.data["lowest_supported_version"]
        == settings.GCAPI_LOWEST_SUPPORTED_VERSION
    )
