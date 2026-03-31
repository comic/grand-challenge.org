import pytest

from tests.factories import TeamFactory, TeamMemberFactory
from tests.utils import (
    assert_viewname_redirect,
    assert_viewname_status,
    get_view_for_user,
    validate_admin_or_participant_view,
    validate_open_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "view", ["teams:list", "teams:create", "teams:member-create"]
)
def test_admin_or_participant_permissions(client, two_challenge_sets, view):
    team = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant,
    )
    if view in ("teams:detail", "teams:member-create"):
        pk = team.pk
    else:
        pk = None
    validate_admin_or_participant_view(
        viewname=view,
        reverse_kwargs={"pk": pk},
        two_challenge_set=two_challenge_sets,
        client=client,
    )


@pytest.mark.django_db
def test_open_views(client, challenge_set):
    team = TeamFactory(
        challenge=challenge_set.challenge, owner=challenge_set.participant
    )
    validate_open_view(
        viewname="teams:detail",
        reverse_kwargs={"pk": team.pk},
        challenge_set=challenge_set,
        client=client,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["teams:update", "teams:delete"])
def test_team_update_delete_permissions(
    client, two_challenge_sets, view, settings
):
    team = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant,
    )
    TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant1,
    )

    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        viewname=view,
        reverse_kwargs={"pk": team.pk},
    )

    tests = [
        (403, two_challenge_sets.challenge_set_1.non_participant),
        (200, two_challenge_sets.challenge_set_1.participant),
        (403, two_challenge_sets.challenge_set_1.participant1),
        (200, two_challenge_sets.challenge_set_1.creator),
        (200, two_challenge_sets.challenge_set_1.admin),
        (403, two_challenge_sets.challenge_set_2.non_participant),
        (403, two_challenge_sets.challenge_set_2.participant),
        (403, two_challenge_sets.challenge_set_2.participant1),
        (403, two_challenge_sets.challenge_set_2.creator),
        (403, two_challenge_sets.challenge_set_2.admin),
        (200, two_challenge_sets.admin12),
        (403, two_challenge_sets.participant12),
        (200, two_challenge_sets.admin1participant2),
    ]
    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_sets.challenge_set_1.challenge,
            client=client,
            user=test[1],
            viewname=view,
            reverse_kwargs={"pk": team.pk},
        )


@pytest.mark.django_db
def test_team_member_delete_permissions(client, two_challenge_sets, settings):
    team = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant,
    )
    team_member = TeamMemberFactory(
        team=team, user=two_challenge_sets.challenge_set_1.participant1
    )

    # No user
    assert_viewname_redirect(
        redirect_url=settings.LOGIN_URL,
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        viewname="teams:member-delete",
        reverse_kwargs={"pk": team_member.pk},
    )

    tests = [
        (403, two_challenge_sets.challenge_set_1.non_participant),
        (200, two_challenge_sets.challenge_set_1.participant),
        (200, two_challenge_sets.challenge_set_1.participant1),
        (200, two_challenge_sets.challenge_set_1.creator),
        (200, two_challenge_sets.challenge_set_1.admin),
        (403, two_challenge_sets.challenge_set_2.non_participant),
        (403, two_challenge_sets.challenge_set_2.participant),
        (403, two_challenge_sets.challenge_set_2.participant1),
        (403, two_challenge_sets.challenge_set_2.creator),
        (403, two_challenge_sets.challenge_set_2.admin),
        (200, two_challenge_sets.admin12),
        (403, two_challenge_sets.participant12),
        (200, two_challenge_sets.admin1participant2),
    ]
    for test in tests:
        assert_viewname_status(
            code=test[0],
            challenge=two_challenge_sets.challenge_set_1.challenge,
            client=client,
            user=test[1],
            viewname="teams:member-delete",
            reverse_kwargs={"pk": team_member.pk},
        )


@pytest.mark.django_db
@pytest.mark.parametrize("team_name", ["test_team_name"])
def test_team_creation(client, two_challenge_sets, team_name):
    response = get_view_for_user(
        viewname="teams:create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.challenge_set_1.participant,
        data={"name": team_name},
    )
    assert response.status_code == 302
    response = get_view_for_user(
        url=response.url,
        client=client,
        user=two_challenge_sets.challenge_set_1.participant,
    )
    assert response.status_code == 200
    assert team_name in response.rendered_content.lower()


@pytest.mark.django_db
def test_team_member_addition(client, two_challenge_sets):
    team = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant,
    )
    assert two_challenge_sets.challenge_set_1.participant in team.get_members()
    assert (
        two_challenge_sets.challenge_set_1.participant1
        not in team.get_members()
    )
    # Participant1 requests to join team
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.challenge_set_1.participant1,
        reverse_kwargs={"pk": team.pk},
    )
    assert (
        two_challenge_sets.challenge_set_1.participant1 in team.get_members()
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_unique_membership(client, two_challenge_sets):
    team = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant,
    )
    team1 = TeamFactory(
        challenge=two_challenge_sets.challenge_set_1.challenge,
        owner=two_challenge_sets.challenge_set_1.participant1,
    )
    # Try to create a new team, should be denied
    response = get_view_for_user(
        viewname="teams:create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.challenge_set_1.participant,
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
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.challenge_set_1.participant1,
        reverse_kwargs={"pk": team.pk},
    )
    assert response.status_code == 200
    assert (
        "You are already a member of another team for this challenge"
        in response.rendered_content
    )
    # participant12 should be able to create a team in their challenge and join
    # another team
    response = get_view_for_user(
        viewname="teams:create",
        challenge=two_challenge_sets.challenge_set_2.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.participant12,
        data={"name": "thisteamshouldbecreated"},
    )
    assert response.status_code == 302
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.participant12,
        reverse_kwargs={"pk": team.pk},
    )
    assert response.status_code == 302
    assert two_challenge_sets.participant12 in team.get_members()
    response = get_view_for_user(
        viewname="teams:member-create",
        challenge=two_challenge_sets.challenge_set_1.challenge,
        client=client,
        method=client.post,
        user=two_challenge_sets.participant12,
        reverse_kwargs={"pk": team1.pk},
    )
    assert response.status_code == 200
    assert (
        "You are already a member of another team for this challenge"
        in response.rendered_content
    )
