import datetime

import pytest

from grandchallenge.challenges.forms import (
    HTMX_BLANK_CHOICE_KEY,
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
        "inference_time_limit_in_minutes": 11,
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
        "expected_number_of_teams": 100,
        "average_size_of_test_image_in_mb": 10,
        "phase_1_number_of_submissions_per_team": 10,
        "phase_2_number_of_submissions_per_team": 1,
        "phase_1_number_of_test_images": 100,
        "phase_2_number_of_test_images": 500,
        "number_of_tasks": 1,
    }
    form = ChallengeRequestBudgetUpdateForm(
        data=data, instance=challenge_request
    )
    assert not form.is_valid()
    assert "inference_time_limit_in_minutes" in form.errors.keys()

    data2 = {
        "expected_number_of_teams": 100,
        "inference_time_limit_in_minutes": 10,
        "algorithm_selectable_gpu_type_choices": [
            HTMX_BLANK_CHOICE_KEY,
            "A10G",
            "T4",
        ],
        "algorithm_maximum_settable_memory_gb": 32,
        "average_size_of_test_image_in_mb": 10,
        "phase_1_number_of_submissions_per_team": 10,
        "phase_2_number_of_submissions_per_team": 1,
        "phase_1_number_of_test_images": 100,
        "phase_2_number_of_test_images": 500,
        "number_of_tasks": 1,
    }
    form2 = ChallengeRequestBudgetUpdateForm(
        data=data2, instance=challenge_request
    )
    assert form2.is_valid()
