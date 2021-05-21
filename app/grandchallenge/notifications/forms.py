from actstream.actions import unfollow
from actstream.models import Follow
from django import forms
from django.contrib.auth import get_user_model

from grandchallenge.notifications.models import Notification


class NotificationForm(forms.Form):
    MARK_READ = "MARK_READ"
    MARK_UNREAD = "MARK_UNREAD"
    REMOVE = "REMOVE"
    CHOICES = (
        (MARK_READ, "Mark as read"),
        (MARK_UNREAD, "Mark as unread"),
        (REMOVE, "Remove notification"),
    )
    notification = forms.ModelChoiceField(
        queryset=Notification.objects.all(), widget=forms.HiddenInput()
    )
    action = forms.ChoiceField(choices=CHOICES, widget=forms.HiddenInput())

    def update(self):
        if self.cleaned_data["action"] == NotificationForm.MARK_READ:
            n = Notification.objects.filter(
                id=self.cleaned_data["notification"].id
            ).get()
            n.read = True
            n.save()
        elif self.cleaned_data["action"] == NotificationForm.MARK_UNREAD:
            n = Notification.objects.filter(
                id=self.cleaned_data["notification"].id
            ).get()
            n.read = False
            n.save()
        elif self.cleaned_data["action"] == NotificationForm.REMOVE:
            Notification.objects.filter(
                id=self.cleaned_data["notification"].id
            ).delete()


class SubscriptionForm(forms.Form):
    UNFOLLOW_TOPIC = "UNFOLLOW_TOPIC"
    UNFOLLOW_FORUM = "UNFOLLOW_FORUM"
    UNFOLLOW_USER = "UNFOLLOW_USER"
    CHOICES = (
        (UNFOLLOW_TOPIC, "Unfollow topic"),
        (UNFOLLOW_FORUM, "Unfollow forum"),
        (UNFOLLOW_USER, "Unfollow user"),
    )
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(), widget=forms.HiddenInput()
    )
    subscription_object = forms.ModelChoiceField(
        queryset=Follow.objects.all(), widget=forms.HiddenInput()
    )
    action = forms.ChoiceField(choices=CHOICES, widget=forms.HiddenInput())

    def update(self):
        if self.cleaned_data["action"] == SubscriptionForm.UNFOLLOW_TOPIC:
            unfollow(
                self.cleaned_data["user"],
                self.cleaned_data["subscription_object"].follow_object,
            )
        if self.cleaned_data["action"] == SubscriptionForm.UNFOLLOW_FORUM:
            unfollow(
                self.cleaned_data["user"],
                self.cleaned_data["subscription_object"].follow_object,
            )
        if self.cleaned_data["action"] == SubscriptionForm.UNFOLLOW_USER:
            unfollow(
                self.cleaned_data["user"],
                self.cleaned_data["subscription_object"].follow_object,
            )
