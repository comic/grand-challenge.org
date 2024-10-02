import pytest
from tests.factories import ChallengeFactory, UserFactory
from tests.utils import get_view_for_user


@pytest.mark.django_db
def test_registration_question_answer_export(client):
    ch = ChallengeFactory()
    admin, participant, non_part_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, non_part_user):
        response = get_view_for_user(
            viewname="api:registration-question-answer-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert (
            response.status_code == 403
        ), "Only admins are allowed to see the list"

    response = get_view_for_user(
        viewname="api:registration-question-answer-list",
        client=client,
        challenge=ch,
        user=admin,
    )

    assert response.status_code == 200, "Admin is allowed to see the list"
    data = response.context_data

    # rq = RegistrationQuestionFactory(challenge=ch)
    # rr = RegistrationRequestFactory(challenge=ch, user=non_part_user)

    # # Create the answer
    # findable_answer = "A very unique line which should be findable anywhere"
    # assert (
    #     str.encode(findable_answer) not in response.content
    # ), "Sanity: answer is not already findable"
    # RegistrationQuestionAnswer.objects.create(
    #     question=rq,
    #     registration_request=rr,
    #     answer=findable_answer,
    # )

    # get_view_for_user(
    #     viewname="api:reader-studies-answer-list",
    #     params={"question__reader_study": str(rs.pk)},
    #     user=editor,
    #     client=client,
    #     method=client.get,
    #     HTTP_ACCEPT="text/csv",
    # )
