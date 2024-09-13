from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)
from tests.factories import (
    ChallengeFactory,
    RegistrationQuestionFactory,
    RegistrationRequestFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "questions,context",
    (
        (
            (
                {
                    "question_text": "Foo",
                },
                {
                    "question_text": "Bar",
                },
            ),
            nullcontext(),
        ),
        (
            (
                {
                    "question_text": "Foo",
                    "schema": {"type": "integer"},
                },
            ),
            nullcontext(),
        ),
        (  # Duplicate text
            (
                {
                    "question_text": "Foo",
                },
                {
                    "question_text": "Foo",
                },
            ),
            pytest.raises(ValidationError),
        ),
        (  # Invalid schema
            (
                {
                    "question_text": "Foo",
                    "schema": {
                        "type": "string",
                        "minLength": -5,  # Invalid: minLength cannot be negative
                    },
                },
            ),
            pytest.raises(ValidationError),
        ),
    ),
)
def test_registration_question_validation(questions, context):
    ch = ChallengeFactory()

    with context:
        for question in questions:
            rq = RegistrationQuestion(
                challenge=ch,
                **question,
            )
            rq.full_clean()
            rq.save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "question,answer,context",
    (
        (
            {},
            "foo",
            nullcontext(),
        ),
        (
            {
                "schema": {"type": "integer"},
            },
            1,
            nullcontext(),
        ),
        (
            {
                "required": False,
            },
            "",
            nullcontext(),
        ),
        (
            {
                "schema": {"type": "integer"},
                "required": False,
            },
            "",
            nullcontext(),
        ),
        (
            {},
            1,  # Only string by default schema
            pytest.raises(ValidationError),
        ),
        (
            {
                "schema": {"type": "integer"},
            },
            "foo",  # Not an integer
            pytest.raises(ValidationError),
        ),
        (
            {
                "required": True,
            },
            "",
            pytest.raises(ValidationError),
        ),
    ),
)
def test_registration_question_answer_validation(question, answer, context):
    rq = RegistrationQuestionFactory(**question)
    rr = RegistrationRequestFactory(challenge=rq.challenge)

    rqa = RegistrationQuestionAnswer(
        registration_request=rr,
        question=rq,
        answer=answer,
    )

    with context:
        rqa.full_clean()


@pytest.mark.django_db
def test_registration_question_double_answer():
    rq = RegistrationQuestionFactory()
    rr = RegistrationRequestFactory(challenge=rq.challenge)

    RegistrationQuestionAnswer.objects.create(
        registration_request=rr, question=rq, answer=""
    )

    with pytest.raises(IntegrityError):
        RegistrationQuestionAnswer.objects.create(
            registration_request=rr,
            question=rq,
            answer="Foo",
        )


@pytest.mark.django_db
def test_registration_question_answer_challenge_contraint():
    ch_a = ChallengeFactory()
    ch_b = ChallengeFactory()

    rq_ch_a = RegistrationQuestionFactory(challenge=ch_a)
    rr_ch_b = RegistrationRequestFactory(challenge=ch_b)

    rqa = RegistrationQuestionAnswer(
        question=rq_ch_a, registration_request=rr_ch_b, answer="answer"
    )

    with pytest.raises(ValidationError):
        rqa.full_clean()

    # Not a problem if we exclude the fields
    rqa.full_clean(exclude=["challenge"])
    rqa.full_clean(exclude=["registration_request"])


@pytest.mark.django_db
def test_registration_question_deletion():
    rq = RegistrationQuestionFactory()
    rq.delete()
    assert not RegistrationQuestion.objects.filter(
        pk=rq.pk
    ).exists(), "Can delete question without any answers"  # Sanity

    rq = RegistrationQuestionFactory()
    rr = RegistrationRequestFactory(challenge=rq.challenge)
    rqa = RegistrationQuestionAnswer.objects.create(
        question=rq,
        registration_request=rr,
        answer="Foo",
    )

    assert RegistrationQuestionAnswer.objects.filter(
        pk=rqa.pk
    ).exists(), "Prior, the answer exists"  # Sanity

    rq.delete()

    assert not RegistrationQuestionAnswer.objects.filter(
        pk=rqa.pk
    ).exists(), "Deleting question -> deletes answer"

    assert not RegistrationQuestion.objects.filter(
        pk=rq.pk
    ).exists(), "Answered question is indeed deleted"  # Sanity

    assert RegistrationRequest.objects.filter(
        pk=rr.pk
    ).exists, "Registration request still exists"
