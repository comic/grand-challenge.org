import pytest

from grandchallenge.participants.forms import RegistrationRequestForm
from grandchallenge.participants.models import (
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationQuestionFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_registration_request_form_no_questions():
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity
    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "0",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "0",
            "registration_question_answers-MAX_NUM_FORMS": "0",
        },
    )
    assert form.is_valid()
    form.save()

    assert RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Should have a registration request"


@pytest.mark.django_db
def test_registration_request_form_with_questions():
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity

    rq1 = RegistrationQuestionFactory(challenge=challenge, required=False)
    rq2 = RegistrationQuestionFactory(challenge=challenge)
    rq3 = RegistrationQuestionFactory(challenge=challenge)

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "3",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "3",
            "registration_question_answers-MAX_NUM_FORMS": "3",
            "registration_question_answers-0-answer": "",
            "registration_question_answers-1-answer": "answer_1",
            "registration_question_answers-2-answer": "answer_2",
        },
    )

    assert form.is_valid()
    rr = form.save()

    for rq, answer in zip(
        (rq1, rq2, rq3), ("", "answer_1", "answer_2"), strict=True
    ):
        assert (
            RegistrationQuestionAnswer.objects.filter(
                registration_request=rr, question=rq, answer=answer
            ).count()
            == 1
        ), "Answer stored is the answer that was posted"


@pytest.mark.django_db
def test_registration_request_form_partial_data():
    challenge = ChallengeFactory()
    user = UserFactory()

    assert not RegistrationRequest.objects.filter(
        user=user
    ).exists(), "Starts with no requests"  # Sanity

    RegistrationQuestionFactory(challenge=challenge)
    RegistrationQuestionFactory(challenge=challenge)
    RegistrationQuestionFactory(challenge=challenge, required=False)

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "3",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "3",
            "registration_question_answers-MAX_NUM_FORMS": "3",
            "registration_question_answers-0-answer": "answer_0",
        },
    )

    assert (
        not form.is_valid()
    ), "Form should not be valid with missing data of required answer"

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "3",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "3",
            "registration_question_answers-MAX_NUM_FORMS": "3",
            "registration_question_answers-0-answer": "answer_0",
            "registration_question_answers-1-answer": "answer_1",
        },
    )

    assert (
        form.is_valid()
    ), "Form should be valid when only missing data of non-required answer"

    form.save()

    assert (
        RegistrationQuestionAnswer.objects.count() == 3
    ), "All answers were created"


@pytest.mark.django_db
def test_registration_request_form_incorrect_format():
    challenge = ChallengeFactory()
    user = UserFactory()

    rq = RegistrationQuestionFactory(
        challenge=challenge, schema={"type": "integer"}
    )

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "1",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "1",
            "registration_question_answers-MAX_NUM_FORMS": "1",
            "registration_question_answers-0-answer": "answer",
        },
    )

    assert (
        not form.is_valid()
    ), "Form should not be valid with incorrect formated answer"

    assert (
        len(form.answer_formset.errors) == 1
        and "answer" in form.answer_formset.errors[0]
    ), "Only error should point towards the question"
    assert (
        "incorrect format"
        in form.answer_formset.errors[0]["answer"][0].lower()
    ), "Should be correct error about incorrect format"

    form = RegistrationRequestForm(
        challenge=challenge,
        user=user,
        data={
            "registration_question_answers-TOTAL_FORMS": "1",
            "registration_question_answers-INITIAL_FORMS": "0",
            "registration_question_answers-MIN_NUM_FORMS": "1",
            "registration_question_answers-MAX_NUM_FORMS": "1",
            "registration_question_answers-0-answer": "1",
        },
    )

    assert form.is_valid(), "With correct format, form should be valid"
    rr = form.save()

    rqa = RegistrationQuestionAnswer.objects.get(
        registration_request=rr, question=rq
    )
    assert rqa.answer == 1, "Answer stored in correct format"
