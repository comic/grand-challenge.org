from django.forms import ModelForm, TextInput

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.participants.models import RegistrationQuestion


class RegistrationQuestionForm(SaveFormInitMixin, ModelForm):

    class Meta:
        model = RegistrationQuestion
        fields = (
            "question_text",
            "question_help_text",
            "required",
            "schema",
        )
        widgets = {
            "question_text": TextInput,
            "question_help_text": TextInput,
            "schema": JSONEditorWidget(),
        }

    def __init__(self, *args, challenge, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            self.instance.challenge = challenge
