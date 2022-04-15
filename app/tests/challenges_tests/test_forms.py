import datetime

import pytest

from grandchallenge.challenges.forms import ChallengeRequestForm
from grandchallenge.challenges.utils import ChallengeTypeChoices
from tests.factories import UserFactory


@pytest.mark.django_db
def test_challenge_request_type_2_budget_fields_required():
    user = UserFactory.build()
    # fill all fields except for budget fields
    # for type 1 this form is valid
    data = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "challenge_type": ChallengeTypeChoices.T1,
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

    # for type 2, the budget fields need to be filled
    data2 = {
        "creator": user,
        "title": "Test request",
        "short_name": "example1234",
        "challenge_type": ChallengeTypeChoices.T2,
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
