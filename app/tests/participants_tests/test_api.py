import pytest
from guardian.shortcuts import remove_perm

from grandchallenge.participants.models import (
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationQuestionFactory,
    RegistrationRequestFactory,
    UserFactory,
)
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_request_api_list(client):
    ch = ChallengeFactory()
    admin, participant, non_part_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    rq_0 = RegistrationQuestionFactory(challenge=ch, question_text="Foo")
    rq_1 = RegistrationQuestionFactory(challenge=ch, question_text="No Foo")

    remove_perm(
        "view_registrationquestion", ch.admins_group, rq_1
    )  # non-permitted viewable question

    RegistrationRequestFactory(
        challenge=ch, user=participant, status=RegistrationRequest.ACCEPTED
    )  # Note: has no answer to the questions, should still show in the export

    rr_1 = RegistrationRequestFactory(challenge=ch, user=non_part_user)

    RegistrationQuestionAnswer.objects.create(
        question=rq_0,
        registration_request=rr_1,
        answer="bar",
    )
    RegistrationQuestionAnswer.objects.create(
        question=rq_1,
        registration_request=rr_1,
        answer="no bar",
    )

    response = get_view_for_user(
        viewname="api:registration-request-list",
        client=client,
        user=admin,
    )

    assert response.status_code == 200, "Admin can query api for list"

    result = response.json()

    assert result["count"] == 2

    # Check content
    registration_request = result["results"][-1]

    assert "created" in registration_request
    assert "changed" in registration_request

    assert registration_request["challenge"] == ch.short_name
    assert registration_request["registration_status"] == "Pending"
    assert (
        registration_request["user"]["user"]["username"]
        == non_part_user.username
    )

    question_answers = registration_request["registration_question_answers"]
    assert len(question_answers) == 1
    assert question_answers[0]["question"]["question_text"] == "Foo"
    assert question_answers[0]["answer"] == "bar"


@pytest.mark.django_db
def test_registration_request_api_list_filtering(client):
    ch_0 = ChallengeFactory()
    admin_0, participant_0, non_part_user = UserFactory.create_batch(3)
    ch_0.add_admin(admin_0)
    ch_0.add_participant(participant_0)

    RegistrationRequestFactory(challenge=ch_0, user=participant_0)
    RegistrationRequestFactory(challenge=ch_0, user=non_part_user)

    # Create another challenge
    ch_1 = ChallengeFactory()
    admin_ch1, participant_1 = UserFactory.create_batch(2)
    ch_1.add_admin(admin_ch1)
    ch_1.add_participant(participant_1)
    RegistrationRequestFactory(challenge=ch_1, user=participant_1)

    # First admin is admin of both
    ch_1.add_admin(admin_0)

    for usr in (participant_0, non_part_user):
        response = get_view_for_user(
            viewname="api:registration-request-list",
            client=client,
            user=usr,
        )

        assert response.status_code == 200, "Non admins can query api"
        assert response.json()["count"] == 0, "Non admins get no challenges"

    response = get_view_for_user(
        viewname="api:registration-request-list",
        client=client,
        user=admin_ch1,
    )
    assert (
        response.json()["count"] == 1
    ), "Alt admin can only see one challenge"

    response = get_view_for_user(
        viewname="api:registration-request-list",
        client=client,
        user=admin_0,
    )

    assert response.status_code == 200, "Admin is allowed to see list"
    assert (
        response.json()["count"] == 3
    ), "Admin can see both challenge' requests"

    response = get_view_for_user(
        viewname="api:registration-request-list",
        data={"challenge__short_name": ch_1.short_name},
        client=client,
        user=admin_0,
    )
    assert response.status_code == 200, "Admin is allowed to see list"
    result = response.json()

    assert result["count"] == 1, "Admin can filter for a challenge"
    assert result["results"][0]["challenge"] == ch_1.short_name
