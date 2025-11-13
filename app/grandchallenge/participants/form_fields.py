from django.core.exceptions import ValidationError
from django.forms import JSONField, TextInput
from django.forms.fields import InvalidJSONInput
from django.utils.html import escape


class RegistrationQuestionAnswerField(JSONField):
    empty_value = InvalidJSONInput("")

    def __init__(self, *, registration_question, widget=TextInput, **kwargs):
        self.registration_question = registration_question

        kwargs.update(
            {
                "label": registration_question.question_text,
                "required": registration_question.required,
                "help_text": escape(registration_question.question_help_text),
            }
        )

        if "initial" not in kwargs:
            kwargs["initial"] = self.empty_value
        else:
            if isinstance(str, kwargs["initial"]):
                kwargs["initial"] = InvalidJSONInput(kwargs["initial"])

        super().__init__(widget=widget, **kwargs)

    def to_python(self, value):
        if value is None or value == "":
            return self.empty_value

        # Handle the presence or absence of double quotes
        try:
            quoted = value.startswith('"') and value.endswith('"')
            result = super().to_python(value)
            if quoted:
                return f'"{result}"'  # noqa: B907
            else:
                return result
        except ValidationError as e:
            if e.code == "invalid" and "Enter a valid JSON" in str(e):
                # Try if a string interpretation would work
                quote_escaped_value = value.replace('"', '\\"')
                return super().to_python(
                    f'"{quote_escaped_value}"'  # noqa: B907
                )
            raise e
