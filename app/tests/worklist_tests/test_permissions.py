import pytest

from tests.factories import WorklistFactory, WorklistSetFactory
from tests.utils import validate_staff_only_view

"""" Tests the permission access for Patient Forms """


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "worklists:worklist-list",
        "worklists:worklist-create",
        "worklists:worklist-update",
        "worklists:worklist-delete",
    ],
)
def test_worklist_form_access(view, client):
    reverse_kwargs = {}
    if view in ("worklists:worklist-update", "worklists:worklist-delete"):
        worklist = WorklistFactory()
        reverse_kwargs.update({"pk": worklist.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "worklists:set-list",
        "worklists:set-create",
        "worklists:set-update",
        "worklists:set-delete",
    ],
)
def test_worklist_set_form_access(view, client):
    reverse_kwargs = {}
    if view in ("worklists:set-update", "worklists:set-delete"):
        set = WorklistSetFactory()
        reverse_kwargs.update({"pk": set.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )
