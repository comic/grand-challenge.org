from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from guardian.utils import get_anonymous_user

from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.direct_messages.models import (
    Conversation,
    DirectMessage,
    Mute,
)


class ConversationForm(forms.ModelForm):
    def __init__(self, *args, participants, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.layout.append(
            StrictButton(
                '<i class="far fa-comment"></i> Message User',
                type="submit",
                css_class="btn btn-primary",
            )
        )

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

        if existing := Conversation.objects.annotate(
            total_participants_count=Count("participants", distinct=True),
            relevant_participants_count=Count(
                "participants",
                filter=Q(participants__in=participants),
                distinct=True,
            ),
        ).filter(
            total_participants_count=len(participants),
            relevant_participants_count=len(participants),
        ):
            self.existing_conversations = existing
            raise ValidationError(
                "Conversation already exists", code="CONVERSATION_EXISTS"
            )

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


class MuteForm(forms.ModelForm):
    conversation = forms.ModelChoiceField(
        queryset=Conversation.objects.none(), widget=forms.HiddenInput()
    )

    def __init__(self, *args, source, target, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["source"].queryset = get_user_model().objects.filter(
            pk=source.pk
        )
        self.fields["source"].initial = source
        self.fields["source"].disabled = True
        self.fields["source"].widget = forms.HiddenInput()

        self.fields["target"].queryset = get_user_model().objects.filter(
            pk=target.pk
        )
        self.fields["target"].initial = target
        self.fields["target"].disabled = True
        self.fields["target"].widget = forms.HiddenInput()

        self.fields["conversation"].queryset = filter_by_permission(
            queryset=Conversation.objects.all(),
            user=source,
            codename="view_conversation",
        )

    def clean(self):
        cleaned_data = super().clean()

        if Mute.objects.filter(
            source=cleaned_data["source"], target=cleaned_data["target"]
        ).exists():
            raise ValidationError("Mute already exists")

        return cleaned_data

    class Meta:
        model = Mute
        fields = (
            "source",
            "target",
        )
