import pytest

from tests.worklists_tests.factories import WorklistFactory
from tests.utils import get_view_for_user, validate_staff_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "worklists:create",
        "worklists:detail",
        "worklists:delete",
        "worklists:update",
        "worklists:display",
    ],
)
def test_worklist_form_access(view, client):
    reverse_kwargs = {}
    if view in ("worklists:update", "worklists:detail", "worklists:delete"):
        worklist = WorklistFactory()
        reverse_kwargs.update({"pk": worklist.pk})

    validate_staff_only_view(
        viewname=view, client=client, reverse_kwargs=reverse_kwargs
    )
