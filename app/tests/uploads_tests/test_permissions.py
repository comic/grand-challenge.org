import pytest

from tests.utils import validate_admin_only_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'uploads:list',
    ]
)
def test_upload_list(view, client, TwoChallengeSets):
    reverse_kwargs = {}

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )
