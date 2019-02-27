import pytest

from tests.worklists_tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import validate_staff_only_view

"""" Tests the permission access for Patient Forms """


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
