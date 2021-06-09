from actstream.actions import follow, unfollow
from actstream.models import Follow
from django import forms
from django.contrib.auth import get_user_model
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

# from grandchallenge.notifications.models import Notification


# class NotificationForm(forms.Form):
#     MARK_READ = "MARK_READ"
#     MARK_UNREAD = "MARK_UNREAD"
#     REMOVE = "REMOVE"
#     CHOICES = (
#         (MARK_READ, "Mark as read"),
#         (MARK_UNREAD, "Mark as unread"),
#         (REMOVE, "Remove notification"),
#     )
#     notification = forms.ModelChoiceField(
#         queryset=Notification.objects.all(), widget=forms.HiddenInput()
#     )
#     action = forms.ChoiceField(choices=CHOICES, widget=forms.HiddenInput())
#
#     def update(self):
#         if self.cleaned_data["action"] == NotificationForm.MARK_READ:
#             n = Notification.objects.filter(
#                 id=self.cleaned_data["notification"].id
#             ).get()
#             n.read = True
#             n.save()
#         elif self.cleaned_data["action"] == NotificationForm.MARK_UNREAD:
#             n = Notification.objects.filter(
#                 id=self.cleaned_data["notification"].id
#             ).get()
#             n.read = False
#             n.save()
#         elif self.cleaned_data["action"] == NotificationForm.REMOVE:
#             Notification.objects.filter(
#                 id=self.cleaned_data["notification"].id
#             ).delete()


class SubscriptionForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all(), widget=forms.HiddenInput()
    )
    subscription_object = forms.ModelChoiceField(
        queryset=Follow.objects.all(),
        widget=forms.HiddenInput(),
        required=False,
    )
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.all(),
        widget=forms.HiddenInput(),
        required=False,
    )
    forum = forms.ModelChoiceField(
        queryset=Forum.objects.all(),
        widget=forms.HiddenInput(),
        required=False,
    )

    def unsubscribe(self):
        unfollow(
            self.cleaned_data["user"],
            self.cleaned_data["subscription_object"].follow_object,
        )

    def subscribe(self):
        if self.cleaned_data["topic"]:
            follow(
                user=self.cleaned_data["user"],
                obj=self.cleaned_data["topic"],
                actor_only=False,
                send_action=False,
            )
        elif self.cleaned_data["forum"]:
            follow(
                user=self.cleaned_data["user"],
                obj=self.cleaned_data["forum"],
                actor_only=False,
                send_action=False,
            )
