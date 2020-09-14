from django.forms import BooleanField, HiddenInput
from machina.apps.forum_conversation.forms import (
    PostForm as BasePostForm,
    TopicForm as BaseTopicForm,
)


class PostForm(BasePostForm):
    enable_signature = BooleanField(
        widget=HiddenInput(), initial=True, label="", required=False
    )


class TopicForm(BaseTopicForm):
    enable_signature = BooleanField(
        widget=HiddenInput(), initial=True, label="", required=False
    )
