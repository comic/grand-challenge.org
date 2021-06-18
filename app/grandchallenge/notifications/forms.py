from actstream.models import Follow
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic
from machina.apps.forum_permission.handler import PermissionHandler

from grandchallenge.core.forms import SaveFormInitMixin


class FollowForm(SaveFormInitMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.perm_handler = PermissionHandler()
        super().__init__(*args, **kwargs)

    def check_permissions(self, requesting_user):
        user = self.cleaned_data["user"]
        obj_id = self.cleaned_data["object_id"]

        if self.cleaned_data["content_type"] == ContentType.objects.get(
            app_label="forum", model="forum"
        ):
            perm = self.perm_handler.can_read_forum(
                Forum.objects.filter(id=obj_id).get(), requesting_user
            )
        elif self.cleaned_data["content_type"] == ContentType.objects.get(
            app_label="forum_conversation", model="topic"
        ):
            perm = self.perm_handler.can_subscribe_to_topic(
                Topic.objects.filter(id=obj_id).get(), requesting_user
            )
        if user != requesting_user:
            raise ValidationError("You cannot create this subscription!")

        if not perm:
            raise ValidationError("You cannot create this subscription!")

    class Meta:
        model = Follow
        fields = ("user", "content_type", "object_id", "actor_only")
