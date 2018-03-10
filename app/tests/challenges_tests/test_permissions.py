import pytest

from comicsite.core.urlresolvers import reverse
from tests.utils import validate_logged_in_view


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'challenges:create',
        'challenges:list',
    ]
)
def test_challenge_list_permissions(view, client, ChallengeSet):

    validate_logged_in_view(
        url=reverse(view),
        challenge_set=ChallengeSet,
        client=client,
    )
