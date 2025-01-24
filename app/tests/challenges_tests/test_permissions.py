import pytest

from grandchallenge.challenges.models import OnboardingTask
from grandchallenge.subdomains.utils import reverse
from grandchallenge.verifications.models import Verification
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    OnboardingTaskFactory,
    UserFactory,
)
from tests.utils import (
    get_view_for_user,
    validate_admin_only_view,
    validate_logged_in_view,
)


@pytest.mark.django_db
@pytest.mark.parametrize("view", ["challenges:users-list"])
def test_challenge_logged_in_permissions(view, client, challenge_set):
    validate_logged_in_view(
        url=reverse(view), challenge_set=challenge_set, client=client
    )


@pytest.mark.django_db
def test_challenge_update_permissions(client, two_challenge_sets):
    validate_admin_only_view(
        two_challenge_set=two_challenge_sets,
        viewname="challenge-update",
        client=client,
    )


@pytest.mark.django_db
def test_request_challenge_only_when_verified(client):
    user = UserFactory()
    assert not Verification.objects.filter(user=user)
    response = get_view_for_user(
        client=client, viewname="challenges:requests-create", user=user
    )
    assert response.status_code == 403
    Verification.objects.create(user=user, is_verified=True)
    response = get_view_for_user(
        client=client, viewname="challenges:requests-create", user=user
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "viewname",
    [
        "challenges:requests-detail",
        "challenges:requests-status-update",
        "challenges:requests-budget-update",
    ],
)
@pytest.mark.django_db
def test_view_and_update_challenge_request(
    client, viewname, challenge_reviewer
):
    challenge_request = ChallengeRequestFactory()
    user = UserFactory()
    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"pk": challenge_request.pk},
        user=user,
    )
    assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    if "detail" in viewname:
        assert response.status_code == 200
        assert "Edit budget fields" not in str(response.content)
        assert "Budget estimate" not in str(response.content)
    else:
        assert response.status_code == 403

    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200
    if "detail" in viewname:
        assert "Edit budget fields" in str(response.content)
        assert "Budget estimate" in str(response.content)


@pytest.mark.django_db
def test_challenge_request_list_view_permissions(client, challenge_reviewer):
    r1, r2 = ChallengeRequestFactory.create_batch(2)
    # requester can only view their own request
    response = get_view_for_user(
        viewname="challenges:requests-list",
        client=client,
        method=client.get,
        user=r1.creator,
    )
    assert response.status_code == 200
    assert len(response.context["object_list"]) == 1
    assert r1.title in str(response.context["object_list"])
    assert r2.title not in str(response.context["object_list"])

    # challenge reviewer can view all requests
    response = get_view_for_user(
        viewname="challenges:requests-list",
        client=client,
        method=client.get,
        user=challenge_reviewer,
    )
    assert response.status_code == 200
    assert r1.title in str(response.context["object_list"])
    assert r2.title in str(response.context["object_list"])


@pytest.mark.django_db
@pytest.mark.parametrize(
    "responsible,permitted",
    (
        (None, True),  # Default
        (OnboardingTask.ResponsiblePartyChoices.SUPPORT, False),
        (OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS, True),
    ),
)
def test_onboarding_task_completion_permissions(responsible, permitted):
    ch = ChallengeFactory()
    user = UserFactory()

    kwargs = {}
    if responsible:
        kwargs["responsible_party"] = responsible

    task = OnboardingTaskFactory(challenge=ch, **kwargs)

    # Sanity
    assert not user.has_perm("complete_onboaringtask", task)
    if responsible:
        assert task.responsible == responsible

    ch.add_admin(user)
    assert user.has_perm("complete_onboaringtask", task) == permitted
