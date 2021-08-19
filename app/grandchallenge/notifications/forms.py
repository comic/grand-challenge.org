from actstream.models import Follow
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from guardian.utils import get_anonymous_user
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic
from machina.apps.forum_permission.handler import PermissionHandler

from grandchallenge.core.forms import SaveFormInitMixin


class FollowForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.perm_handler = PermissionHandler()

        self.user = user
        self.fields["user"].queryset = get_user_model().objects.filter(
            pk=self.user.pk
        )
        self.fields["user"].initial = self.user

    def clean_user(self):
        user = self.cleaned_data["user"]
        if user == get_anonymous_user():
            raise ValidationError(
                "Subscription cannot be created for this user"
            )
        return user

    def clean(self):
        cleaned_data = super().clean()

        try:
            obj_id = cleaned_data["object_id"]
        except KeyError:
            raise ValidationError("You cannot create this subscription!")

        if cleaned_data["content_type"] == ContentType.objects.get(
            app_label="forum", model="forum"
        ):
            perm = self.perm_handler.can_read_forum(
                Forum.objects.filter(id=obj_id).get(), self.user
            )
        elif cleaned_data["content_type"] == ContentType.objects.get(
            app_label="forum_conversation", model="topic"
        ):
            perm = self.perm_handler.can_subscribe_to_topic(
                Topic.objects.filter(id=obj_id).get(), self.user
            )

        if not perm:
            raise ValidationError("You cannot create this subscription!")

        return cleaned_data

    class Meta:
        model = Follow
        fields = ("user", "content_type", "object_id", "actor_only")
        widgets = {
            "user": forms.HiddenInput(),
            "content_type": forms.HiddenInput(),
            "object_id": forms.HiddenInput(),
            "actor_only": forms.HiddenInput(),
        }
