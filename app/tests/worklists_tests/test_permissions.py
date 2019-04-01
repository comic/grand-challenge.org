import pytest

from guardian.shortcuts import assign_perm
from tests.factories import UserFactory
from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import get_view_for_user, validate_staff_only_view

""" Tests the permission access for Worklist API Tables """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view, factory",
    [
        "worklists:list",
        "worklists:set",
    ],
)
def test_worklist_api_access(view, factory, client):
    permitted_user = UserFactory()
    blocked_user = UserFactory()
    instance = factory()

    # Assigns permissions to user
    model_name = factory._meta.model._meta.model_name
    for permission_type in factory._meta.model._meta.default_permissions:
        permission_name = f"{permission_type}_{model_name}"
        assign_perm(permission_name, permitted_user, instance)

    # Asserts whether or not both users have access
    permitted_response = get_view_for_user(
        viewname="worklists:list-create",
        client=client,
        method=client.get,
        user=permitted_user,
    )

    blocked_response = permitted_response = get_view_for_user(
        viewname="worklists:list-create",
        client=client,
        method=client.get,
        user=blocked_user,
        kwargs={"pk": instance.pk}
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
