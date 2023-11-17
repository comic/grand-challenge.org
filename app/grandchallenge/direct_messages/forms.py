from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from guardian.utils import get_anonymous_user

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.direct_messages.models import Conversation, DirectMessage


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


class DirectMessageForm(forms.ModelForm):
    def __init__(self, *args, conversation, sender, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout.append(Submit("save", "Send"))

        self.fields["conversation"].queryset = filter_by_permission(
            queryset=Conversation.objects.filter(pk=conversation.pk),
            user=sender,
            codename="create_conversation_direct_message",
        )
        self.fields["conversation"].initial = conversation
        self.fields["conversation"].disabled = True
        self.fields["conversation"].widget = forms.HiddenInput()

        self.fields["sender"].queryset = get_user_model().objects.filter(
            pk=sender.pk
        )
        self.fields["sender"].initial = sender
        self.fields["sender"].disabled = True
        self.fields["sender"].widget = forms.HiddenInput()

        unread_by = conversation.participants.exclude(pk=sender.pk)

        self.fields["unread_by"].queryset = unread_by
        self.fields["unread_by"].initial = unread_by
        self.fields["unread_by"].disabled = True
        self.fields["unread_by"].widget = forms.MultipleHiddenInput()

        self.fields["message"].widget = forms.Textarea(
            attrs={
                "placeholder": "Write a message...",
                "rows": "3",
                "style": "resize:none;",
            }
        )
        self.fields["message"].label = ""

    class Meta:
        model = DirectMessage
        fields = (
            "conversation",
            "sender",
            "unread_by",
            "message",
        )


class DirectMessageReportSpamForm(forms.ModelForm):
    is_reported_as_spam = forms.BooleanField(
        initial=True, required=True, widget=forms.HiddenInput
    )

    class Meta:
        model = DirectMessage
        fields = ("is_reported_as_spam",)
