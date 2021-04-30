import pytest

from tests.utils import validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        "update",
        "pages:list",
        "admins:list",
        "participants:list",
        "participants:registration-list",
        "evaluation:phase-update",
        "evaluation:phase-create",
    ],
)
def test_admins_see_links(view, client, two_challenge_sets):
    if view == "evaluation:phase-update":
        reverse_kwargs = {
            "slug": two_challenge_sets.challenge_set_1.challenge.phase_set.get().slug,
        }
    else:
        reverse_kwargs = {}
    validate_admin_only_view(
        viewname=view,
        two_challenge_set=two_challenge_sets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )
