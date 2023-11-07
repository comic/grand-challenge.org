from django import forms
from django.core.exceptions import ValidationError
from guardian.utils import get_anonymous_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.direct_messages.models import Conversation


class ConversationForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, participants, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["participants"].queryset = participants
        self.fields["participants"].initial = participants
        self.fields["participants"].disabled = True
        self.fields["participants"].widget = forms.MultipleHiddenInput()

    def clean_participants(self):
        participants = self.cleaned_data["participants"]

        if get_anonymous_user() in participants:
            raise ValidationError("You cannot add this user!")

        if len(participants) < 2:
            raise ValidationError("Too few participants")

        # TODO check that a conversation with this set of users does not exist

        return participants

    class Meta:
        model = Conversation
        fields = ("participants",)
