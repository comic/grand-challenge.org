import pytest

from tests.utils import (
    validate_admin_only_view,
)


@pytest.mark.django_db
def test_page_list(client, TwoChallengeSets):
    validate_admin_only_view(
        viewname='pages:list',
        two_challenge_set=TwoChallengeSets,
        client=client
    )
