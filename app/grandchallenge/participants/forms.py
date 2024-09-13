from django.core.exceptions import ValidationError
from django.db.transaction import on_commit
from django.forms import HiddenInput, ModelForm, TextInput

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.participants.form_fields import RegistrationQuestionField
from grandchallenge.participants.models import (
    RegistrationQuestion,
    RegistrationQuestionAnswer,
    RegistrationRequest,
)


class RegistrationRequestForm(ModelForm):
    class Meta:
        model = RegistrationRequest
        fields = (
            "user",
            "challenge",
        )
        widgets = {
            "user": HiddenInput(),
            "challenge": HiddenInput(),
        }

    def __init__(self, *args, challenge, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user"].initial = user
        self.fields["user"].disabled = True
        self.fields["challenge"].initial = challenge
        self.fields["challenge"].disabled = True

        self._registration_questions = RegistrationQuestion.objects.filter(
            challenge=challenge
        )

        for q in self._registration_questions:
            self.fields[str(q.pk)] = RegistrationQuestionField(
                registration_question=q
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
        for answer in self._registration_question_answers:
            try:
                answer.full_clean(
                    exclude=[
                        "registration_request",  # Not saved at this point yet
                    ],
                )
            except ValidationError as e:
                answer_error = e.error_dict.get("answer")
                if answer_error:
                    self.add_error(str(answer.question.pk), answer_error)
                else:
                    raise e
        return result

    def _save_questions(self):
        self.instance.refresh_from_db()
        try:
            for answer in self._registration_question_answers:
                answer.full_clean()
                answer.save()
        except Exception as e:
            self.instance.delete()  # Also deletes already created answers
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
