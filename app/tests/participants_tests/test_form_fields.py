import pytest
from django.utils.safestring import SafeString

from grandchallenge.participants.form_fields import RegistrationQuestionField
from grandchallenge.participants.models import RegistrationQuestion


def test_registration_field():
    rq = RegistrationQuestion(
        question_text="Foo",
        question_help_text="<script></script>",
        required=False,
    )
    field = RegistrationQuestionField(registration_question=rq)

    assert isinstance(
        field.help_text, SafeString
    ), "Help text should be escaped"

    assert (field.label, field.required) == (
        rq.question_text,
        rq.required,
    ), "Field settings sourced from question"

    assert field.initial == ""


@pytest.mark.parametrize(
    "value, expected_python",
    (
        ("", ""),
        ("Foo", "Foo"),
        ('{"foo": "bar"}', {"foo": "bar"}),
        ("1", 1),
        ("1.42", 1.42),
    ),
)
def test_registration_field_to_python(value, expected_python):
    field = RegistrationQuestionField(
        registration_question=RegistrationQuestion(question_text="Foo")
    )
    generated_python = field.to_python(value)
    assert generated_python == expected_python
