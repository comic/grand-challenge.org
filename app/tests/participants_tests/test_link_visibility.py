import pytest

from comicsite.core.urlresolvers import reverse
from tests.factories import RegistrationRequestFactory
from tests.utils import validate_admin_only_text_in_page, get_view_for_user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'participants:registration-list',
        'participants:list',
    ]
)
def test_admins_see_links(view, client, TwoChallengeSets):
    url = reverse('challenge-homepage',
                  args=[TwoChallengeSets.ChallengeSet1.challenge.short_name])

    expected = reverse(
        view,
        args=[TwoChallengeSets.ChallengeSet1.challenge.short_name]
    )

    validate_admin_only_text_in_page(
        url=url,
        expected_text=f'"{str(expected)}"',
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_join_page_links(client, ChallengeSet):
    tests = [
        (ChallengeSet.non_participant, 'Click here to join'),
        (ChallengeSet.participant, 'You are already participating'),
    ]

    for test in tests:
        response = get_view_for_user(
            viewname='participants:registration-create',
            client=client,
            user=test[0],
            challenge=ChallengeSet.challenge,
        )

        assert test[1] in response.rendered_content

        rr = RegistrationRequestFactory(user=test[0],
                                        project=ChallengeSet.challenge)

        response = get_view_for_user(
            viewname='participants:registration-create',
            client=client,
            user=test[0],
            challenge=ChallengeSet.challenge,
        )

        assert rr.status_to_string() in response.rendered_content
