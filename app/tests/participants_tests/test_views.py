import pytest

from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_question_list_view(client):
    ch = ChallengeFactory(hidden=False)
    admin, participant, anom_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, anom_user):
        response = get_view_for_user(
            viewname="participants:registration-questions",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert response.status_code == 403, "Non admin cannot view"

    response = get_view_for_user(
        viewname="participants:registration-questions",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 0

    RegistrationQuestion.objects.create(
        challenge=ch,
        question_text="Foo",
        question_help_text="",
        required=True,
        schema="",
    )
    RegistrationQuestion.objects.create(
        challenge=ch,
        question_text="Bar",
        question_help_text="",
        required=False,
        schema="",
    )

    answered_question = RegistrationQuestion.objects.create(
        challenge=ch,
        question_text="answered",
        question_help_text="",
        required=True,
        schema="",
    )
    rr = RegistrationRequestFactory(user=anom_user, challenge=ch)
    RegistrationQuestionAnswer.objects.create(
        question=answered_question,
        registration_request=rr,
        answer="An answer",
    )

    response = get_view_for_user(
        viewname="participants:registration-questions",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 3
