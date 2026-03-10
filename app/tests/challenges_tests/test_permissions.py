import pytest

from grandchallenge.challenges.models import ChallengeRequest, OnboardingTask
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
        "challenges:requests-update",
        "challenges:requests-submit",
        "challenges:requests-process",
        "challenges:requests-budget-update",
    ],
)
@pytest.mark.django_db
def test_challenge_request_regular_user_cannot_access(client, viewname):
    challenge_request = ChallengeRequestFactory()
    user = UserFactory()
    response = get_view_for_user(
        client=client,
        viewname=viewname,
        reverse_kwargs={"pk": challenge_request.pk},
        user=user,
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_challenge_request_creator_viewing_and_updating(client):
    challenge_request = ChallengeRequestFactory(title="Not Foo")
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    assert response.status_code == 200

    # Test rendering of reviewer only sections
    assert "Edit Budget Estimate" not in str(response.content)
    assert "Budget estimate" not in str(response.content)

    # Test that creator can update when in DRAFT status
    # Build form data with all required fields
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
        data={  # Minimal data to pass validation
            "title": "Foo",
            "short_name": challenge_request.short_name,
            "contact_email": challenge_request.contact_email,
            "abstract": challenge_request.abstract,
        },
    )
    assert response.status_code == 302  # Redirect on successful update
    challenge_request.refresh_from_db()
    assert (
        challenge_request.title == "Foo"
    ), "Sanity check that title was updated"

    # Test that creator can submit when in DRAFT status
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-submit",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
        data={"status": ChallengeRequest.ChallengeRequestStatusChoices.DRAFT},
    )
    assert response.status_code == 200

    # Submit it so that it is no longer editable by the creator
    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )
    challenge_request.save()

    # Can no longer update the status
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-process",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
        },
    )
    assert response.status_code == 403

    # Creator cannot update budget at any stage
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-budget-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
    )
    assert response.status_code == 403

    # Can no longer update the title
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_request.creator,
        data={  # Minimal data to pass validation
            "title": "Bar",
            "short_name": challenge_request.short_name,
            "contact_email": challenge_request.contact_email,
            "abstract": challenge_request.abstract,
        },
    )
    assert response.status_code == 200
    assert "Only challenge requests in draft status can be edited." in str(
        response.context["form"].errors
    )
    challenge_request.refresh_from_db()
    assert (
        challenge_request.title == "Foo"
    ), "Title should not have been updated due to status change"


@pytest.mark.django_db
def test_challenge_request_reviewer_can_access_all(client, challenge_reviewer):
    challenge_request = ChallengeRequestFactory(title="Not Foo")
    response = get_view_for_user(
        client=client,
        viewname="challenges:requests-detail",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
    )
    assert response.status_code == 200

    # Test rendering of reviewer only sections
    assert "Edit Budget Estimate" in str(response.content)
    assert "Budget estimate" in str(response.content)

    # Test that reviewer can update when in DRAFT status

    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={  # Minimal data to pass validation
            "title": "Foo",
            "short_name": challenge_request.short_name,
            "contact_email": challenge_request.contact_email,
            "abstract": challenge_request.abstract,
        },
    )
    assert response.status_code == 302  # Redirect on successful update
    challenge_request.refresh_from_db()
    assert (
        challenge_request.title == "Foo"
    ), "Sanity check that title was updated"

    # Test that reviewer can also submit when in DRAFT status
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-submit",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={"status": ChallengeRequest.ChallengeRequestStatusChoices.DRAFT},
    )
    assert response.status_code == 200

    # Submit it
    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )
    challenge_request.save()

    # Can no still update the status
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-process",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={
            "status": ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED
        },
    )
    assert response.status_code == 200

    # Reviewer can update budget at any stage
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-budget-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={
            "task_ids": "[1, 2]",
            "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
            "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
            "average_size_test_case_mb_for_tasks": "[10, 100]",
            "inference_time_average_minutes_for_tasks": "[5, 10]",
            "task_id_for_phases": "[1, 1, 2, 2]",
            "number_of_teams_for_phases": "[500, 500, 500, 500]",
            "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
            "number_of_test_cases_for_phases": "[3, 100, 3, 100]",
        },
    )
    assert response.status_code == 200

    # Can no longer update the title
    response = get_view_for_user(
        client=client,
        method=client.post,
        viewname="challenges:requests-update",
        reverse_kwargs={"pk": challenge_request.pk},
        user=challenge_reviewer,
        data={  # Minimal data to pass validation
            "title": "Bar",
            "short_name": challenge_request.short_name,
            "contact_email": challenge_request.contact_email,
            "abstract": challenge_request.abstract,
        },
    )
    assert response.status_code == 200
    assert "Only challenge requests in draft status can be edited." in str(
        response.context["form"].errors
    )
    challenge_request.refresh_from_db()
    assert (
        challenge_request.title == "Foo"
    ), "Title should not have been updated due to status change"


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
    "expected_responsible_party,permitted",
    (
        (None, True),  # Default
        (OnboardingTask.ResponsiblePartyChoices.SUPPORT, False),
        (OnboardingTask.ResponsiblePartyChoices.CHALLENGE_ORGANIZERS, True),
    ),
)
def test_onboarding_task_completion_permissions(
    expected_responsible_party, permitted
):
    ch = ChallengeFactory()
    user = UserFactory()

    kwargs = {}
    if expected_responsible_party:
        kwargs["responsible_party"] = expected_responsible_party

    task = OnboardingTaskFactory(challenge=ch, **kwargs)

    # Sanity
    assert not user.has_perm("change_onboardingtask", task)
    assert not user.has_perm("view_onboardingtask", task)

    if expected_responsible_party:
        assert task.responsible_party == expected_responsible_party

    ch.add_admin(user)
    assert user.has_perm("change_onboardingtask", task) == permitted
    assert user.has_perm("view_onboardingtask", task) == permitted
