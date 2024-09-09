import json
from functools import partial

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
    admin, participant, user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    for usr in (participant, user, admin):
        response = get_view_for_user(
            viewname="participants:registration-question-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert (
            response.status_code == 200
        ), f"{usr} should be able to view the question list"
        assert len(response.context_data["object_list"]) == 0  # Sanity

    RegistrationQuestionFactory(challenge=ch, required=False)
    RegistrationQuestionFactory(challenge=ch)

    for usr, num_questions in ((participant, 0), (user, 0), (admin, 2)):
        response = get_view_for_user(
            viewname="participants:registration-question-list",
            client=client,
            challenge=ch,
            user=usr,
        )
        assert (
            response.status_code == 200
        ), f"{usr} should still be able to view the question list"
        assert (
            len(response.context_data["object_list"]) == num_questions
        ), f"{usr} should see the correct number of questions"


@pytest.mark.django_db
def test_registration_question_create_view(client):
    ch = ChallengeFactory()

    _test_registration_question_view(
        client,
        challenge=ch,
        viewname="participants:registration-question-create",
    )


@pytest.mark.django_db
def test_registration_question_update_view(client):
    ch = ChallengeFactory()

    question = RegistrationQuestionFactory(question_text="foo", challenge=ch)

    assert question.question_text == "foo"

    _test_registration_question_view(
        client,
        challenge=ch,
        viewname="participants:registration-question-update",
        request_kwargs={
            "reverse_kwargs": {"pk": question.pk},
        },
    )

    question.refresh_from_db()
    assert question.question_text != "foo"


def _test_registration_question_view(
    client, challenge, viewname, request_kwargs=None
):
    request_kwargs = request_kwargs or {}

    admin, participant, non_part_user = UserFactory.create_batch(3)

    challenge.add_admin(admin)
    challenge.add_participant(participant)

    def get(user):
        return get_view_for_user(
            viewname=viewname,
            client=client,
            challenge=challenge,
            user=user,
            **request_kwargs,
        )

    for usr in (participant, non_part_user):
        response = get(user=usr)
        assert (
            response.status_code == 403
        ), "Non admin should not be able to get"

    response = get(user=admin)
    assert response.status_code == 200, "Admin should be able to get"

    post_data = {
        "question_text": "foo bar",
        "question_help_text": "bar foo",
        "required": False,
        "schema": json.dumps({"type": "integer"}),
    }

    def post(user):
        return get_view_for_user(
            viewname=viewname,
            client=client,
            method=client.post,
            challenge=challenge,
            user=user,
            data=post_data,
            **request_kwargs,
        )

    for usr in (participant, non_part_user):
        response = post(user=usr)
        assert (
            response.status_code == 403
        ), "Non admin should not be able to post"

    response = post(user=admin)

    assert response.status_code == 302, "Valid form redirects for an admin"

    question = RegistrationQuestion.objects.get(challenge=challenge)
    for key, value in post_data.items():
        if key == "schema":
            value = json.loads(value)
        if key == "challenge":
            value = challenge
        assert (
            getattr(question, key) == value
        ), "Updated value should match posted data"


@pytest.mark.django_db
def test_registration_question_delete_view(client):
    ch = ChallengeFactory()
    admin, participant, non_part_user = UserFactory.create_batch(3)
    ch.add_admin(admin)
    ch.add_participant(participant)

    rq = RegistrationQuestionFactory(question_text="foo", challenge=ch)

    get = partial(
        get_view_for_user,
        viewname="participants:registration-question-delete",
        client=client,
        challenge=ch,
        reverse_kwargs={"pk": rq.pk},
    )

    def get_delete(user):
        return get(user=user)

    def post_delete(user):
        return get(user=user, method=client.post)

    for usr in (participant, non_part_user):
        for method in (get_delete, post_delete):
            response = method(user=usr)
            assert (
                response.status_code == 403
            ), f"Non admins should not be able to {method.__name__}"

    response = get_delete(user=admin)
    assert response.status_code == 200, "Admin should be able to get delete"

    response = post_delete(user=admin)
    assert response.status_code == 302, "Admin should be able to post delete"

    assert not RegistrationQuestion.objects.filter(
        pk=rq.pk
    ).exists(), "Question should be removed after delete post"


@pytest.mark.django_db
def test_registration_request_list_view(client):
    ch = ChallengeFactory()
    admin, anom_user_0, anom_user_1 = UserFactory.create_batch(3)
    ch.add_admin(admin)

    rq = RegistrationQuestionFactory(question_text="foo", challenge=ch)

    rr_0 = RegistrationRequestFactory(challenge=ch, user=anom_user_0)

    answer = "A very unique line which should be findable anywhere"
    RegistrationQuestionAnswer.objects.create(
        registration_request=rr_0,
        question=rq,
        answer=answer,
    )

    # Note: this request has no answers associated with it
    RegistrationRequestFactory(challenge=ch, user=anom_user_1)

    response = get_view_for_user(
        viewname="participants:registration-list",
        client=client,
        challenge=ch,
        user=admin,
    )
    assert response.status_code == 200, "Registration list can be gotton OK"

    assert (
        str.encode(answer) in response.content
    ), "The answer is rendered somewhere on the page"
