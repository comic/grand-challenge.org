from django.forms import HiddenInput, ModelForm, TextInput

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import JSONEditorWidget
from grandchallenge.participants.models import RegistrationQuestion


class RegistrationQuestionForm(SaveFormInitMixin, ModelForm):

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

    def __init__(self, *args, challenge=None, **kwargs):
        super().__init__(*args, **kwargs)

        if challenge:
            self.fields["challenge"].initial = challenge
        self.fields["challenge"].disabled = True
