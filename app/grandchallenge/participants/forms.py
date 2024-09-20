from django.forms import (
    HiddenInput,
    ModelForm,
    TextInput,
    inlineformset_factory,
)

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.participants.form_fields import (
    RegistrationQuestionAnswerField,
)
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

        self.answer_formset = self._get_answer_formset(
            challenge,
            data=kwargs.get("data"),
        )

    def _get_answer_formset(self, challenge, data):
        questions = challenge.registration_questions.all()
        answer_formset_factory = inlineformset_factory(
            parent_model=self._meta.model,
            model=RegistrationQuestionAnswer,
            form=RegistrationQuestionAnswerForm,
            max_num=questions.count(),
            min_num=questions.count(),
            absolute_max=questions.count(),
            extra=0,
            can_delete=False,
            can_delete_extra=False,
        )
        return answer_formset_factory(
            instance=self.instance,
            data=data,
            initial=[{"question": q} for q in questions],
            form_kwargs={
                # Formsets disabled the use of the attribute by default,
                # since we don't allow for 'extra' forms
                # we can forcefully allow it.
                "use_required_attribute": True,
            },
        )

    def is_valid(self):
        return super().is_valid() and self.answer_formset.is_valid()

    def full_clean(self, *args, **kwargs):
        super().full_clean(*args, **kwargs)
        self.answer_formset.full_clean()

        # Show formset-level validation errors
        for error in self.answer_formset.non_form_errors():
            self.add_error(field=None, error=error)

    def save(self, *args, **kwargs):
        registration_request = super().save(*args, **kwargs)

        # By default, formsets only save changed or non-empty
        # forms. Short-circuit saving to ensure it saves empty
        # answers
        for form in self.answer_formset.forms:
            self.answer_formset.save_new(form)

        return registration_request


class RegistrationQuestionAnswerForm(ModelForm):

    class Meta:
        model = RegistrationQuestionAnswer
        fields = ("answer",)

    def __init__(self, *args, initial, **kwargs):
        super().__init__(*args, initial=initial, **kwargs)

        self.instance.question = initial["question"]

        self.fields["answer"] = RegistrationQuestionAnswerField(
            registration_question=self.instance.question
        )


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
