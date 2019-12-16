from collections import namedtuple

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions

from grandchallenge.subdomains.utils import reverse
from tests.factories import UserFactory
from tests.utils import assert_viewname_status


@pytest.fixture(name="api_users_set")
def api_users_set():
    """Creates four user types with varying permissions."""
    api_users_sets = namedtuple(
        "api_users", ["user", "staff", "super_user", "anonymous"]
    )

    user = UserFactory(is_staff=False, is_superuser=False)
    staff = UserFactory(is_staff=True, is_superuser=False)
    super_user = UserFactory(is_staff=True, is_superuser=True)
    anonymous = AnonymousUser()

    return api_users_sets(user, staff, super_user, anonymous)


@pytest.mark.parametrize("user", ["user", "staff", "super_user", "anonymous"])
@pytest.mark.parametrize(
    "method",
    ("POST", "PUT", "DELETE", "TRACE", "PATCH") + permissions.SAFE_METHODS,
)
@pytest.mark.parametrize(
    "schema, schema_format",
    [
        ("schema-json", ".json"),
        ("schema-json", ".yaml"),
        ("schema-docs", None),
    ],
)
@pytest.mark.django_db
def test_api_permissions(
    client, user, method, schema, schema_format, api_users_set
):
    if method == "OPTIONS" and schema == "schema-docs":
        pytest.xfail(
            "These tests are known to fail with with: "
            "django.core.exceptions.ImproperlyConfigured: "
            "Returned a template response with no `template_name` "
            "attribute set on either the view or response"
        )
    expected_responses_per_user_for_unsafe_methods = dict(
        user=403, staff=403, super_user=405, anonymous=401
    )
    kwargs = dict(format=schema_format) if schema == "schema-json" else None
    assert_viewname_status(
        code=expected_responses_per_user_for_unsafe_methods[user]
        if method not in permissions.SAFE_METHODS
        else 200,
        url=reverse(f"api:{schema}", kwargs=kwargs),
        client=client,
        user=getattr(api_users_set, user),
        method=getattr(client, method.lower()),
    )
