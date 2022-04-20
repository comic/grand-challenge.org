import datetime

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.challenges.forms import ChallengeRequestForm
from grandchallenge.challenges.models import ChallengeRequest
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


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

    with pytest.raises(
        ValidationError,
        match=f"There already is a challenge with short name: {type_1_challenge_request.short_name}",
    ):
        _ = get_view_for_user(
            client=client,
            method=client.post,
            viewname="challenges:requests-update",
            reverse_kwargs={"pk": type_1_challenge_request.pk},
            data={
                "status": type_1_challenge_request.ChallengeRequestStatusChoices.ACCEPTED
            },
            user=challenge_reviewer,
        )
