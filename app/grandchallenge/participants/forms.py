
from functools import cached_property

from django.core.exceptions import ValidationError
from django.db.transaction import on_commit
from django.forms import HiddenInput, JSONField, ModelForm, TextInput
from django.forms.fields import InvalidJSONInput
from django.utils.html import escape


from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)


class RegistrationQuestionField(JSONField):
    empty_value = InvalidJSONInput("")

    def __init__(self, *, registration_question, **kwargs):
        self.registration_question = registration_question

        kwargs.update(
            {
                "label": registration_question.question_text,
                "required": registration_question.required,
                "help_text": escape(registration_question.question_help_text),
                "widget": TextInput,
            }
        )

        if "initial" not in kwargs:
            kwargs["initial"] = self.empty_value
        else:
            if isinstance(str, kwargs["initial"]):
                kwargs["initial"] = InvalidJSONInput(kwargs["initial"])

        super().__init__(**kwargs)

    def to_python(self, value):
        if value is None or value == "":
            return self.empty_value
        try:
            return super().to_python(value)
        except ValidationError:
            # We assume it is a string
            return value


class RegistrationRequestForm(ModelForm):
    class Meta:
        model = RegistrationRequest
        fields = ()

    def __init__(self, *args, challenge, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.challenge = challenge
        self.instance.user = user

        for q in self._registration_questions:
            self.fields[str(q.pk)] = RegistrationQuestionField(
                registration_question=q
            )

    @cached_property
    def _registration_questions(self):
        return RegistrationQuestion.objects.filter(
            challenge=self.instance.challenge
        )

    @property
    def _registration_question_answers(self):
        for q in self._registration_questions:
            yield RegistrationQuestionAnswer(
                question=q,
                registration_request=self.instance,
                answer=self.cleaned_data.get(str(q.pk), ""),
            )

    def clean(self):
        result = super().clean()
        for rqa in self._registration_question_answers:
            try:
                rqa.full_clean(
                    exclude=[
                        "registration_request",  # Not saved at this point yet
                    ],
                )
            except ValidationError as e:
                answer_error = e.error_dict.get("answer")
                if answer_error:
                    self.add_error(str(rqa.question.pk), answer_error)
                else:
                    raise e
        return result

    def _save_questions(self):
        try:
            for rqa in self._registration_question_answers:
                rqa.full_clean()
                rqa.save()
        except ValidationError as e:
            self.instance.delete()
            raise e

    def save(self, *args, **kwargs):
        result = super().save(self, *args, **kwargs)
        on_commit(self._save_questions)
        return result


class RegistrationQuestionUpdateForm(SaveFormInitMixin, ModelForm):

    class Meta:
        model = RegistrationQuestion
        fields = (
            "challenge",
            "question_text",
            "question_help_text",
            "required",
            "schema",
        )
        widgets = {
            "challenge": HiddenInput(),
            "question_text": TextInput,
            "question_help_text": TextInput,
            "schema": JSONEditorWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["challenge"].disabled = True


class RegistrationQuestionCreateForm(RegistrationQuestionUpdateForm):

    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["challenge"].initial = challenge
