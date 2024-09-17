import pytest

from grandchallenge.participants.form_fields import RegistrationQuestionField
from grandchallenge.participants.models import RegistrationQuestion


def test_registration_field():
    rq = RegistrationQuestion(
        question_text="Foo",
        question_help_text='<div class="test">Hello & Welcome!</div>',
        required=False,
    )
    field = RegistrationQuestionField(registration_question=rq)

    assert (
        field.help_text
        == "&lt;div class=&quot;test&quot;&gt;Hello &amp; Welcome!&lt;/div&gt;"
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
        ('"Foo"', "Foo"),
        ('"Foo', '"Foo'),
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
