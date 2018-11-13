import pytest

from tests.factories import StudyFactory
from tests.utils import validate_logged_in_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "studies:study-list",
        "studies:study-create",
        "studies:study-update",
        "studies:study-delete",
    ],
)
def test_external_challenges_staff_views(client, view):
    if view in ["studies:study-update", "studies:study-delete"]:
        reverse_kwargs = {"short_name": StudyFactory().short_name}
    else:
        reverse_kwargs = {}

    validate_logged_in_view(
        client=client, viewname=view, reverse_kwargs=reverse_kwargs
    )
