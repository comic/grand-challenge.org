import json

import pytest

from grandchallenge.participants.models import RegistrationQuestion
from tests.factories import (
    ChallengeFactory,
    RegistrationQuestionFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_question_list_view(client):
    ch = ChallengeFactory()
    admin, participant, anom_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, anom_user):
        response = get_view_for_user(
            viewname="participants:registration-question-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert response.status_code == 403, "Non admin cannot view"

    response = get_view_for_user(
        viewname="participants:registration-question-list",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 0

    RegistrationQuestionFactory(challenge=ch)
    RegistrationQuestionFactory(challenge=ch, required=True)

    response = get_view_for_user(
        viewname="participants:registration-question-list",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200
    assert len(response.context_data["object_list"]) == 2


@pytest.mark.django_db
def test_registration_question_create_view(client):
    ch = ChallengeFactory()
    admin, participant, anom_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, anom_user):
        response = get_view_for_user(  # GET
            viewname="participants:registration-question-create",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert response.status_code == 403, "Non admin cannot view"

    response = get_view_for_user(  # GET
        viewname="participants:registration-question-create",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200

    assert RegistrationQuestion.objects.filter(challenge=ch).count() == 0

    post_data = {
        "question_text": "foo bar",
        "question_help_text": "bar foo",
        "required": False,
        "schema": json.dumps({"type": "integer"}),
    }

    response = get_view_for_user(  # POST
        viewname="participants:registration-question-create",
        client=client,
        method=client.post,
        challenge=ch,
        user=admin,
        data=post_data,
        follow=True,
    )

    assert response.status_code == 200

    created_question = RegistrationQuestion.objects.get(challenge=ch)
    for key, value in post_data.items():
        if key == "schema":
            value = json.loads(value)
        assert getattr(created_question, key) == value
