import pytest

from guardian.shortcuts import assign_perm, remove_perm
from grandchallenge.subdomains.utils import reverse
from rest_framework.authtoken.models import Token
from tests.factories import UserFactory
from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import get_view_for_user, validate_staff_only_view

""" Tests the permission access for Worklist API Tables """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view, factory",
    [
        ("worklists:list", WorklistFactory),
        ("worklists:set", WorklistSetFactory),
    ],
)
def test_worklist_api_access(view, factory, client):
    user = UserFactory(is_staff=True)
    token = Token.objects.create(user=user).key
    instance = factory()

    # Asserts whether or not both users have access
    url = reverse(view, kwargs={"pk": instance.pk})

    # Assigns permissions to user
    model_name = factory._meta.model._meta.model_name
    for permission_type in factory._meta.model._meta.default_permissions:
        permission_name = f"{permission_type}_{model_name}"
        assign_perm(permission_name, user, instance)

    permitted_response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    # Removes permissions from user
    for permission_type in factory._meta.model._meta.default_permissions:
        permission_name = f"{permission_type}_{model_name}"
        remove_perm(permission_name, user, instance)

    blocked_response = client.get(
        url,
        HTTP_ACCEPT="application/json",
        HTTP_AUTHORIZATION="Token " + token,
    )

    assert permitted_response.status_code == 200
    assert blocked_response.status_code == 403


""" Tests the permission access for Worklist Forms """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "worklists:list-create",
        "worklists:list-remove",
        "worklists:list-update",
        "worklists:list-display",
    ],
)
def test_worklist_form_access(view, client):
    reverse_kwargs = {}
    if view in ("worklists:list-update", "worklists:list-remove"):
        worklist = WorklistFactory()
        reverse_kwargs.update({"pk": worklist.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )


""" Tests the permission access for Worklist Set Forms """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "worklists:set-create",
        "worklists:set-remove",
        "worklists:set-update",
        "worklists:set-display",
    ],
)
def test_worklist_set_form_access(view, client):
    reverse_kwargs = {}
    if view in ("worklists:set-update", "worklists:set-remove"):
        set = WorklistSetFactory()
        reverse_kwargs.update({"pk": set.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )
