import pytest

from comicsite.core.urlresolvers import reverse
from tests.factories import RegistrationRequestFactory
from tests.utils import (
    validate_admin_only_view,
    validate_logged_in_view,
    validate_admin_only_text_in_page,
    get_view_for_user)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'participants:registration-list',
        'participants:registration-update',
        'participants:list',
    ]
)
def test_registration_request_list(view, client, TwoChallengeSets):
    reverse_kwargs = {}
    if view in ('participants:registration-update',):
        rr = RegistrationRequestFactory(
            project=TwoChallengeSets.ChallengeSet1.challenge)
        reverse_kwargs.update({'pk': rr.pk})

    validate_admin_only_view(
        viewname=view,
        two_challenge_set=TwoChallengeSets,
        client=client,
        reverse_kwargs=reverse_kwargs,
    )


@pytest.mark.django_db
def test_registration_request_create(client, ChallengeSet):
    validate_logged_in_view(
        viewname='participants:registration-create',
        challenge_set=ChallengeSet,
        client=client,
    )


@pytest.mark.django_db
def test_admins_see_links(client, TwoChallengeSets):
    url = reverse('challenge-homepage',
                  args=[TwoChallengeSets.ChallengeSet1.challenge.short_name])
    expected = reverse(
        'participants:list',
        args=[TwoChallengeSets.ChallengeSet1.challenge.short_name]
    )

    validate_admin_only_text_in_page(
        url=url,
        expected_text=str(expected),
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_participants_list_is_filtered(client, TwoChallengeSets):
    response = get_view_for_user(
        viewname='participants:list',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        user=TwoChallengeSets.admin12,
    )

    tests = [
        (False, TwoChallengeSets.ChallengeSet1.non_participant),
        (True, TwoChallengeSets.ChallengeSet1.participant),
        (True, TwoChallengeSets.ChallengeSet1.participant1),
        (False, TwoChallengeSets.ChallengeSet1.creator),
        (False, TwoChallengeSets.ChallengeSet1.admin),
        (False, TwoChallengeSets.ChallengeSet2.non_participant),
        (False, TwoChallengeSets.ChallengeSet2.participant),
        (False, TwoChallengeSets.ChallengeSet2.participant1),
        (False, TwoChallengeSets.ChallengeSet2.creator),
        (False, TwoChallengeSets.ChallengeSet2.admin),
        # admin12 is in the response as they're loading the page
        (True, TwoChallengeSets.admin12),
        (True, TwoChallengeSets.participant12),
        (False, TwoChallengeSets.admin1participant2),
    ]

    for test in tests:
        assert (test[1].username in response.rendered_content) == test[0]
