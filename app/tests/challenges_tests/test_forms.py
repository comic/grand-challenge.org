import pytest

from grandchallenge.challenges.forms import (
    ChallengeRequestBudgetUpdateForm,
    ChallengeRequestStatusUpdateForm,
)
from grandchallenge.challenges.models import ChallengeRequest
from tests.factories import ChallengeFactory, ChallengeRequestFactory


@pytest.mark.django_db
def test_accept_challenge_request_duplicate_shortname():
    challenge_request = ChallengeRequestFactory()
    _ = ChallengeFactory(short_name=challenge_request.short_name)
    challenge_request.status = (
        ChallengeRequest.ChallengeRequestStatusChoices.PENDING
    )
    challenge_request.save()

    form = ChallengeRequestStatusUpdateForm(
        data={
            "status": challenge_request.ChallengeRequestStatusChoices.ACCEPTED
        },
        instance=challenge_request,
    )
    assert not form.is_valid()
    assert "There already is a challenge with this name." in str(form.errors)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "challenge_request_status,post_status,validity",
    (
        (  # Submit
            ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
            ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
            True,
        ),
        (  # Process - Accept
            ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
            ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
            True,
        ),
        (  # Process - Reject
            ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
            ChallengeRequest.ChallengeRequestStatusChoices.REJECTED,
            True,
        ),
        (  # Skip submitted
            ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
            ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
            False,
        ),
        (  # Skip submitted
            ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
            ChallengeRequest.ChallengeRequestStatusChoices.REJECTED,
            False,
        ),
        (
            ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
            ChallengeRequest.ChallengeRequestStatusChoices.REJECTED,
            False,
        ),
        (
            ChallengeRequest.ChallengeRequestStatusChoices.REJECTED,
            ChallengeRequest.ChallengeRequestStatusChoices.ACCEPTED,
            False,
        ),
        (  # Cannot unsubmit a request
            ChallengeRequest.ChallengeRequestStatusChoices.PENDING,
            ChallengeRequest.ChallengeRequestStatusChoices.DRAFT,
            False,
        ),
        *(  # Same state transitions are not allowed
            (s, s, False)
            for s in ChallengeRequest.ChallengeRequestStatusChoices
        ),
    ),
)
def test_challenge_request_update_form(
    challenge_request_status, post_status, validity
):
    challenge_request = ChallengeRequestFactory()
    challenge_request.status = challenge_request_status
    challenge_request.save()

    form = ChallengeRequestStatusUpdateForm(
        data={"status": post_status},
        instance=challenge_request,
    )
    if validity:
        assert form.is_valid(), form.errors
    else:
        assert not form.is_valid(), form.errors
        assert "status" in form.errors


@pytest.mark.django_db
def test_budget_update_form():
    challenge_request = ChallengeRequestFactory()
    # all budget fields need to be filled
    data = {
        "task_ids": "[1, 2]",
        "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
        "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
        "average_size_test_case_mb_for_tasks": "[10, 100]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[500, 500, 500, 500]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_cases_for_phases": "[3, 100, 3, 100]",
    }
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )
    assert not form.is_valid()
    assert "inference_time_average_minutes_for_tasks" in form.errors.keys()

    data2 = {
        "task_ids": "[1, 2]",
        "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
        "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
        "average_size_test_case_mb_for_tasks": "[10, 100]",
        "inference_time_average_minutes_for_tasks": "[5, 10]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[500, 500, 500, 500]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_cases_for_phases": "[3, 100, 3, 100]",
    }
    form2 = ChallengeRequestBudgetUpdateForm(
        data=data2, instance=challenge_request
    )
    assert form2.is_valid()


@pytest.mark.parametrize(
    "invalid_data, reason_invalid",
    [
        ({"task_ids": "[1]"}, "not all task ids defined"),
        ({"task_ids": "[1, 1]"}, "task ids are not unique"),
        (
            {"algorithm_maximum_settable_memory_gb_for_tasks": "[32]"},
            "not all tasks defined",
        ),
        (
            {"algorithm_selectable_gpu_type_choices_for_tasks": '["", "T4"]'},
            "not all tasks defined",
        ),
        (
            {"average_size_test_case_mb_for_tasks": "[10]"},
            "not all tasks defined",
        ),
        (
            {"inference_time_average_minutes_for_tasks": "[10]"},
            "not all tasks defined",
        ),
        ({"task_id_for_phases": "[1, 1]"}, "not all task ids used"),
        ({"task_id_for_phases": "[1, 1, 2, 3]"}, "using undefined task id"),
        (
            {"number_of_teams_for_phases": "[10, 10, 10]"},
            "not all phases defined",
        ),
        (
            {"number_of_submissions_per_team_for_phases": "[10, 1, 10]"},
            "not all phases defined",
        ),
        (
            {"number_of_test_cases_for_phases": "[3, 100, 3]"},
            "not all phases defined",
        ),
        (
            {"number_of_teams_for_phases": "[1, 10, 10, 10]"},
            "later phase has more teams",
        ),
        (
            {"number_of_submissions_per_team_for_phases": "[1, 10, 10, 10]"},
            "later phase has more submissions",
        ),
    ],
)
@pytest.mark.django_db
def test_budget_update_form_invalid(invalid_data, reason_invalid):
    challenge_request = ChallengeRequestFactory()
    data = {
        "task_ids": "[1, 2]",
        "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
        "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
        "average_size_test_case_mb_for_tasks": "[10, 100]",
        "inference_time_average_minutes_for_tasks": "[5, 10]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[10, 10, 10, 10]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_cases_for_phases": "[3, 100, 3, 100]",
    }
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )

    assert form.is_valid()

    data.update(invalid_data)
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )

    assert not form.is_valid(), reason_invalid
