import datetime

import pytest

from grandchallenge.challenges.forms import (
    ChallengeRequestForm,
    ChallengeRequestUpdateForm,
)
from grandchallenge.challenges.models import ChallengeRequest
from tests.factories import ChallengeFactory, UserFactory


@pytest.mark.django_db
def test_challenge_request_type_2_fields_required():
    user = UserFactory.build()
    # fill all fields except for budget and input / output fields
    # for type 1 this form is valid
    data = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "challenge_type": ChallengeRequest.ChallengeTypeChoices.T1,
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
    }
    form = ChallengeRequestForm(data=data, creator=user)
    assert form.is_valid()

    # for type 2, these fields need to be filled
    data2 = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "challenge_type": ChallengeRequest.ChallengeTypeChoices.T2,
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
    }
    form2 = ChallengeRequestForm(data=data2, creator=user)
    assert not form2.is_valid()
    assert "For a type 2 challenge, you need to provide" in str(form2.errors)


@pytest.mark.django_db
def test_accept_challenge_request(
    client, challenge_reviewer, type_1_challenge_request
):
    _ = ChallengeFactory(short_name=type_1_challenge_request.short_name)
    form = ChallengeRequestUpdateForm(
        data={
            "status": type_1_challenge_request.ChallengeRequestStatusChoices.ACCEPTED
        },
        instance=type_1_challenge_request,
    )
    assert not form.is_valid()
    assert (
        f"There already is a challenge with short name: {type_1_challenge_request.short_name}"
        in str(form.errors)
    )
