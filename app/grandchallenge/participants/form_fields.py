from django.core.exceptions import ValidationError
from django.forms import JSONField, TextInput
from django.forms.fields import InvalidJSONInput
from django.utils.html import escape


class RegistrationQuestionField(JSONField):
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
        try:
            return super().to_python(value)
        except ValidationError:
            # We assume it is a string
            return value
