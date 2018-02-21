# -*- coding: utf-8 -*-
import pytest

from tests.evaluation_tests.test_views import \
    validate_admin_or_participant_view, get_view_for_user
from tests.factories import TeamFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view",
    [
        'teams:list',
        'teams:create',
        'teams:detail',
        'teams:member-create',
    ]
)
def test_admin_or_participant_permissions(client, TwoChallengeSets, view):
    team = TeamFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                       creator=TwoChallengeSets.ChallengeSet1.participant)

    if view in ('teams:detail', 'teams:member-create',):
        pk = team.pk
    else:
        pk = None

    validate_admin_or_participant_view(viewname=view,
                                       pk=pk,
                                       two_challenge_set=TwoChallengeSets,
                                       client=client)


# TODO: Team Update and Team Member delete permissions


@pytest.mark.django_db
@pytest.mark.parametrize(
    'team_name',
    [
        'test_team_name',
    ]
)
def test_team_creation(client, TwoChallengeSets, team_name):
    response = get_view_for_user(
        viewname='teams:create',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant,
        data={'name': team_name},
    )

    assert response.status_code == 302

    response = get_view_for_user(
        url=response.url,
        client=client,
        method=client.get,
        user=TwoChallengeSets.ChallengeSet1.participant,
    )

    assert response.status_code == 200
    assert team_name in response.rendered_content


@pytest.mark.django_db
def test_team_member_addition(client, TwoChallengeSets):
    team = TeamFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                       creator=TwoChallengeSets.ChallengeSet1.participant)

    assert TwoChallengeSets.ChallengeSet1.participant in team.get_members()
    assert TwoChallengeSets.ChallengeSet1.participant1 not in team.get_members()

    # Participant1 requests to join team
    response = get_view_for_user(
        viewname='teams:member-create',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant1,
        pk=team.pk,
    )

    assert TwoChallengeSets.ChallengeSet1.participant1 in team.get_members()
    assert response.status_code == 302


@pytest.mark.django_db
def test_unique_membership(client, TwoChallengeSets):
    team = TeamFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                       creator=TwoChallengeSets.ChallengeSet1.participant)
    TeamFactory(challenge=TwoChallengeSets.ChallengeSet1.challenge,
                creator=TwoChallengeSets.ChallengeSet1.participant1)

    # Try to create a new team, should be denied
    response = get_view_for_user(
        viewname='teams:create',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant,
        data={'name': 'thisteamshouldnotbecreated'},
    )

    assert response.status_code == 200
    assert 'You are already a member of another team for this challenge' in response.rendered_content

    # Participant1 requests to join team, should be denied
    response = get_view_for_user(
        viewname='teams:member-create',
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant1,
        pk=team.pk,
    )

    assert response.status_code == 200
    assert 'You are already a member of another team for this challenge' in response.rendered_content

    # participant12 should be able to create a team in their challenge and join another
