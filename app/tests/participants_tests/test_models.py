from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
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
def test_registration_question_no_changes_update():
    rq = RegistrationQuestionFactory()
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
            1,  # Only string by default
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
