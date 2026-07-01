import pytest
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet

from grandchallenge.api.routers import APIRouter
from grandchallenge.components.schemas import ANSWER_TYPE_SCHEMA
from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
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
def test_api_lowest_gcapi_version_check(client, settings):
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


@pytest.mark.django_db
def test_api_root_accessible_to_authenticated_user(client):
    user = UserFactory()
    response = assert_viewname_status(
        code=200,
        url=reverse("api:api-root"),
        client=client,
        user=user,
    )
    assert len(response.data) > 0


@pytest.mark.django_db
def test_api_root_not_accessible_to_anonymous_user(client):
    assert_viewname_status(
        code=401,
        url=reverse("api:api-root"),
        client=client,
    )


def test_router_does_not_override_default_permissions_for_registered_views():
    """
    Views registered on the APIRouter that do not explicitly set
    permission_classes must still inherit the global IsAdminUser default.
    Only the root view should have relaxed permissions.
    """
    router = APIRouter()

    class NoPermViewSet(ModelViewSet):
        """A viewset that does not set permission_classes."""

        pass

    router.register(r"test", NoPermViewSet, basename="test")
    urls = router.get_urls()

    view_url = next(u for u in urls if u.name == "test-list")
    view_cls = view_url.callback.cls

    assert view_cls.permission_classes == [IsAdminUser]
