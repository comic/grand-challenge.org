from contextlib import nullcontext

import pytest
from django.core.exceptions import ValidationError

from grandchallenge.participants.models import RegistrationQuestion
from tests.factories import ChallengeFactory


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
