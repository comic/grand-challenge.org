import pytest

from tests.factories import PageFactory
from tests.utils import (
    validate_admin_only_view,
    get_view_for_user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'pages:list',
        'pages:create',
    ]
)
def test_page_admin_permissions(view, client, TwoChallengeSets):
    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client
    )


@pytest.mark.django_db
def test_page_list_filter(client, TwoChallengeSets):
    """ Check that only pages related to this challenge are listed """
    p1 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet1.challenge,
                     title='challenge1page1')
    p2 = PageFactory(comicsite=TwoChallengeSets.ChallengeSet2.challenge,
                     title='challenge2page1')

    response = get_view_for_user(
        viewname='pages:list',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        user=TwoChallengeSets.admin12)

    assert p1.title in response.rendered_content
    assert p2.title not in response.rendered_content

    response = get_view_for_user(
        viewname='pages:list',
        client=client,
        method=client.get,
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        user=TwoChallengeSets.admin12
    )

    assert p1.title not in response.rendered_content
    assert p2.title in response.rendered_content
