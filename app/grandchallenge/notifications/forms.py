from actstream.actions import unfollow
from django import forms
from django.contrib.auth import get_user_model
from django.db.models.query_utils import Q

from grandchallenge.notifications.models import Notification


class NotificationForm(forms.Form):
    MARK_READ = "MARK_READ"
    MARK_UNREAD = "MARK_UNREAD"
    REMOVE = "REMOVE"
    UNFOLLOW = "UNFOLLOW"
    CHOICES = (
        (MARK_READ, "Mark as read"),
        (MARK_UNREAD, "Mark as unread"),
        (REMOVE, "Remove notification"),
        (UNFOLLOW, "Unfollow notification target"),
    )
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(), widget=forms.HiddenInput()
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
        elif self.cleaned_data["action"] == NotificationForm.UNFOLLOW:
            # user will no longer receive notifications for this target in future
            unfollow(
                self.cleaned_data["user"],
                self.cleaned_data["notification"].action.target,
            )
            # delete all notifications relating to this target for this user
            Notification.objects.filter(
                Q(
                    action__target_object_id=self.cleaned_data[
                        "notification"
                    ].action.target.id
                )
                & Q(user_id=self.cleaned_data["user"])
            ).delete()
