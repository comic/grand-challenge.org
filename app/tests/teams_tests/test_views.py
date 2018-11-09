import pytest
from django.conf import settings
from django.test import Client

from tests.factories import TeamFactory, TeamMemberFactory
from tests.utils import (
    get_view_for_user,
    assert_viewname_status,
    assert_viewname_redirect,
    validate_admin_or_participant_view,
    validate_open_view,
)


def validate_owner_or_admin_view(
    *, two_challenge_set, client: Client, **kwargs
):
    """ Assert that a view is only accessible to administrators or participants
    of that particular challenge """
    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_set.ChallengeSet1.challenge,
        client=client,
        **kwargs,
    )
    tests = [
        (403, two_challenge_set.ChallengeSet1.non_participant),
        (200, two_challenge_set.ChallengeSet1.participant),
        (403, two_challenge_set.ChallengeSet1.participant1),
        (200, two_challenge_set.ChallengeSet1.creator),
        (200, two_challenge_set.ChallengeSet1.admin),
        (403, two_challenge_set.ChallengeSet2.non_participant),
        (403, two_challenge_set.ChallengeSet2.participant),
        (403, two_challenge_set.ChallengeSet2.participant1),
        (403, two_challenge_set.ChallengeSet2.creator),
        (403, two_challenge_set.ChallengeSet2.admin),
        (200, two_challenge_set.admin12),
        (403, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]
    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.ChallengeSet1.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


def validate_member_owner_or_admin_view(
    *, two_challenge_set, client: Client, **kwargs
):
    """ Assert that a view is only accessible to administrators or participants
    of that particular challenge """
    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_set.ChallengeSet1.challenge,
        client=client,
        **kwargs,
    )
    tests = [
        (403, two_challenge_set.ChallengeSet1.non_participant),
        (200, two_challenge_set.ChallengeSet1.participant),
        (200, two_challenge_set.ChallengeSet1.participant1),
        (200, two_challenge_set.ChallengeSet1.creator),
        (200, two_challenge_set.ChallengeSet1.admin),
        (403, two_challenge_set.ChallengeSet2.non_participant),
        (403, two_challenge_set.ChallengeSet2.participant),
        (403, two_challenge_set.ChallengeSet2.participant1),
        (403, two_challenge_set.ChallengeSet2.creator),
        (403, two_challenge_set.ChallengeSet2.admin),
        (200, two_challenge_set.admin12),
        (403, two_challenge_set.participant12),
        (200, two_challenge_set.admin1participant2),
    ]
    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_set.ChallengeSet1.challenge,
            client=client,
            user=test[1],
            **kwargs,
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view", ["teams:list", "teams:create", "teams:member-create"]
)
def test_admin_or_participant_permissions(client, TwoChallengeSets, view):
    team = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant,
    )
    if view in ("teams:detail", "teams:member-create"):
        pk = team.pk
    else:
        pk = None
    validate_admin_or_participant_view(
        viewname=view,
        reverse_kwargs={"pk": pk},
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_open_views(client, ChallengeSet):
    team = TeamFactory(
        challenge=ChallengeSet.challenge, owner=ChallengeSet.participant
    )
    validate_open_view(
        viewname="teams:detail",
        reverse_kwargs={"pk": team.pk},
        challenge_set=ChallengeSet,
        client=client,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["teams:update", "teams:delete"])
def test_team_update_delete_permissions(client, TwoChallengeSets, view):
    team = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant,
    )
    TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant1,
    )
    validate_owner_or_admin_view(
        viewname=view,
        reverse_kwargs={"pk": team.pk},
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
def test_team_member_delete_permissions(client, TwoChallengeSets):
    team = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant,
    )
    team_member = TeamMemberFactory(
        team=team, user=TwoChallengeSets.ChallengeSet1.participant1
    )
    validate_member_owner_or_admin_view(
        viewname="teams:member-delete",
        reverse_kwargs={"pk": team_member.pk},
        two_challenge_set=TwoChallengeSets,
        client=client,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("team_name", ["test_team_name"])
def test_team_creation(client, TwoChallengeSets, team_name):
    response = get_view_for_user(
        viewname="teams:create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant,
        data={"name": team_name},
    )
    assert response.status_code == 302
    response = get_view_for_user(
        url=response.url,
        client=client,
        user=TwoChallengeSets.ChallengeSet1.participant,
    )
    assert response.status_code == 200
    assert team_name in response.rendered_content


@pytest.mark.django_db
def test_team_member_addition(client, TwoChallengeSets):
    team = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant,
    )
    assert TwoChallengeSets.ChallengeSet1.participant in team.get_members()
    assert (
        TwoChallengeSets.ChallengeSet1.participant1 not in team.get_members()
    )
    # Participant1 requests to join team
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant1,
        reverse_kwargs={"pk": team.pk},
    )
    assert TwoChallengeSets.ChallengeSet1.participant1 in team.get_members()
    assert response.status_code == 302


@pytest.mark.django_db
def test_unique_membership(client, TwoChallengeSets):
    team = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant,
    )
    team1 = TeamFactory(
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        owner=TwoChallengeSets.ChallengeSet1.participant1,
    )
    # Try to create a new team, should be denied
    response = get_view_for_user(
        viewname="teams:create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant,
        data={"name": "thisteamshouldnotbecreated"},
    )
    assert response.status_code == 200
    assert (
        "You are already a member of another team for this challenge"
        in response.rendered_content
    )
    # Participant1 requests to join team, should be denied
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.ChallengeSet1.participant1,
        reverse_kwargs={"pk": team.pk},
    )
    assert response.status_code == 200
    assert (
        "You are already a member of another team for this challenge"
        in response.rendered_content
    )
    # participant12 should be able to create a team in their challenge and join another
    response = get_view_for_user(
        viewname="teams:create",
        challenge=TwoChallengeSets.ChallengeSet2.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.participant12,
        data={"name": "thisteamshouldbecreated"},
    )
    assert response.status_code == 302
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.participant12,
        reverse_kwargs={"pk": team.pk},
    )
    assert response.status_code == 302
    assert TwoChallengeSets.participant12 in team.get_members()
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=TwoChallengeSets.ChallengeSet1.challenge,
        client=client,
        method=client.post,
        user=TwoChallengeSets.participant12,
        reverse_kwargs={"pk": team1.pk},
    )
    assert response.status_code == 200
    assert (
        "You are already a member of another team for this challenge"
        in response.rendered_content
    )
