from django import forms

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
