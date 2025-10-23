import datetime

import pytest

from grandchallenge.challenges.forms import (
    ChallengeRequestBudgetUpdateForm,
    ChallengeRequestForm,
    ChallengeRequestStatusUpdateForm,
)
from tests.factories import (
    ChallengeFactory,
    ChallengeRequestFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_challenge_request_budget_fields_required():
    user = UserFactory.build()
    # fill all fields except for budget and input / output fields
    data = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + datetime.timedelta(days=1),
        "expected_number_of_participants": 10,
        "abstract": "test",
        "contact_email": "test@test.com",
        "organizers": "test",
        "challenge_setup": "test",
        "data_set": "test",
        "submission_assessment": "test",
        "challenge_publication": "test",
        "code_availability": "test",
        "expected_number_of_teams": 10,
        "number_of_tasks": 1,
        "challenge_fee_agreement": True,
    }
    form = ChallengeRequestForm(data=data, creator=user)
    assert not form.is_valid()

    data2 = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + datetime.timedelta(days=1),
        "expected_number_of_participants": 10,
        "abstract": "test",
        "contact_email": "test@test.com",
        "organizers": "test",
        "challenge_setup": "test",
        "data_set": "test",
        "submission_assessment": "test",
        "challenge_publication": "test",
        "code_availability": "test",
        "expected_number_of_teams": 10,
        "number_of_tasks": 1,
        "challenge_fee_agreement": True,
        "algorithm_inputs": "foo",
        "algorithm_outputs": "foo",
        "average_size_of_test_image_in_mb": 1,
        "inference_time_average_minutes": 11,
        "algorithm_selectable_gpu_type_choices": ["", "A10G", "T4"],
        "algorithm_maximum_settable_memory_gb": 32,
        "phase_1_number_of_submissions_per_team": 1,
        "phase_2_number_of_submissions_per_team": 1,
        "phase_1_number_of_test_images": 1,
        "phase_2_number_of_test_images": 1,
    }
    form2 = ChallengeRequestForm(data=data2, creator=user)
    assert form2.is_valid()


@pytest.mark.django_db
def test_challenge_request_new_fields_filled_from_old_fields():
    user = UserFactory()
    data = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + datetime.timedelta(days=1),
        "abstract": "test",
        "contact_email": "test@test.com",
        "organizers": "test",
        "challenge_setup": "test",
        "data_set": "test",
        "submission_assessment": "test",
        "challenge_publication": "test",
        "code_availability": "test",
        "expected_number_of_teams": 10,
        "number_of_tasks": 2,
        "challenge_fee_agreement": True,
        "algorithm_inputs": "foo",
        "algorithm_outputs": "foo",
        "average_size_of_test_image_in_mb": 1,
        "inference_time_average_minutes": 11,
        "algorithm_selectable_gpu_type_choices": ["", "A10G", "T4"],
        "algorithm_maximum_settable_memory_gb": 32,
        "phase_1_number_of_submissions_per_team": 10,
        "phase_2_number_of_submissions_per_team": 1,
        "phase_1_number_of_test_images": 3,
        "phase_2_number_of_test_images": 300,
    }
    form = ChallengeRequestForm(data=data, creator=user)

    assert form.is_valid(), form.errors

    challenge_request = form.save()

    # deprecated fields are not filled
    assert challenge_request.expected_number_of_teams is None
    assert challenge_request.number_of_tasks is None
    assert challenge_request.average_size_of_test_image_in_mb is None
    assert challenge_request.inference_time_limit_in_minutes is None
    assert challenge_request.algorithm_selectable_gpu_type_choices is None
    assert challenge_request.algorithm_maximum_settable_memory_gb is None
    assert challenge_request.phase_1_number_of_submissions_per_team is None
    assert challenge_request.phase_2_number_of_submissions_per_team is None
    assert challenge_request.phase_1_number_of_test_images is None
    assert challenge_request.phase_2_number_of_test_images is None

    # new fields are filled
    assert (
        challenge_request.algorithm_selectable_gpu_type_choices_for_tasks
        == [["", "A10G", "T4"], ["", "A10G", "T4"]]
    )
    assert (
        challenge_request.algorithm_maximum_settable_memory_gb_for_tasks
        == [32, 32]
    )
    assert challenge_request.average_size_test_image_mb_for_tasks == [1, 1]
    assert challenge_request.inference_time_average_minutes_for_tasks == [
        11,
        11,
    ]
    assert challenge_request.task_ids == [1, 2]
    assert challenge_request.task_id_for_phases == [1, 1, 2, 2]
    assert challenge_request.number_of_teams_for_phases == [10, 10, 10, 10]
    assert challenge_request.number_of_submissions_per_team_for_phases == [
        10,
        1,
        10,
        1,
    ]
    assert challenge_request.number_of_test_images_for_phases == [
        3,
        300,
        3,
        300,
    ]


@pytest.mark.django_db
def test_accept_challenge_request(client, challenge_reviewer):
    challenge_request = ChallengeRequestFactory()
    _ = ChallengeFactory(short_name=challenge_request.short_name)
    form = ChallengeRequestStatusUpdateForm(
        data={
            "status": challenge_request.ChallengeRequestStatusChoices.ACCEPTED
        },
        instance=challenge_request,
    )
    assert not form.is_valid()
    assert "There already is a challenge with this name." in str(form.errors)


@pytest.mark.django_db
def test_budget_update_form():
    challenge_request = ChallengeRequestFactory()
    # all budget fields need to be filled
    data = {
        "task_ids": "[1, 2]",
        "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
        "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
        "average_size_test_image_mb_for_tasks": "[10, 100]",
        # "inference_time_average_minutes_for_tasks": "[5, 10]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[500, 500, 500, 500]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_images_for_phases": "[3, 100, 3, 100]",
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
        "average_size_test_image_mb_for_tasks": "[10, 100]",
        "inference_time_average_minutes_for_tasks": "[5, 10]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[500, 500, 500, 500]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_images_for_phases": "[3, 100, 3, 100]",
    }
    form2 = ChallengeRequestBudgetUpdateForm(
        data=data2, instance=challenge_request
    )
    assert form2.is_valid()


@pytest.mark.parametrize(
    "invalid_data",
    [
        {"task_ids": "[1]"},  # not all task ids defined
        {"task_ids": "[1, 1]"},  # task ids are not unique
        {
            "algorithm_maximum_settable_memory_gb_for_tasks": "[32]"
        },  # not all tasks defined
        {
            "algorithm_selectable_gpu_type_choices_for_tasks": '["", "T4"]'
        },  # not all tasks defined
        {
            "average_size_test_image_mb_for_tasks": "[10]"
        },  # not all tasks defined
        {
            "inference_time_average_minutes_for_tasks": "[10]"
        },  # not all tasks defined
        {"task_id_for_phases": "[1, 1]"},  # not all task ids used
        {"task_id_for_phases": "[1, 1, 2, 3]"},  # using undefined task id
        {
            "number_of_teams_for_phases": "[10, 10, 10]"
        },  # not all phases defined
        {
            "number_of_submissions_per_team_for_phases": "[10, 1, 10]"
        },  # not all phases defined
        {
            "number_of_test_images_for_phases": "[3, 100, 3]"
        },  # not all phases defined
        {
            "number_of_teams_for_phases": "[1, 10, 10, 10]"
        },  # later phase has more teams
        {
            "number_of_submissions_per_team_for_phases": "[1, 10, 10, 10]"
        },  # later phase has more submissions
    ],
)
@pytest.mark.django_db
def test_budget_update_form_invalid(invalid_data):
    challenge_request = ChallengeRequestFactory()
    data = {
        "task_ids": "[1, 2]",
        "algorithm_maximum_settable_memory_gb_for_tasks": "[32, 32]",
        "algorithm_selectable_gpu_type_choices_for_tasks": '[["", "T4"],["", "A10G", "T4"]]',
        "average_size_test_image_mb_for_tasks": "[10, 100]",
        "inference_time_average_minutes_for_tasks": "[5, 10]",
        "task_id_for_phases": "[1, 1, 2, 2]",
        "number_of_teams_for_phases": "[10, 10, 10, 10]",
        "number_of_submissions_per_team_for_phases": "[10, 1, 10, 1]",
        "number_of_test_images_for_phases": "[3, 100, 3, 100]",
    }
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )

    assert form.is_valid()

    data.update(invalid_data)
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )

    assert not form.is_valid()
