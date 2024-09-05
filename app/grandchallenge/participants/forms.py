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
        if (
            not hasattr(self.instance, "challenge")
            or not self.instance.challenge
        ):
            self.instance.challenge = challenge
