from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import CharField, HiddenInput, ModelChoiceField, ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    TopicKindChoices,
)


class ForumTopicForm(SaveFormInitMixin, ModelForm):

    creator = ModelChoiceField(
        widget=HiddenInput(),
        queryset=(
            get_user_model().objects.exclude(
                username=settings.ANONYMOUS_USER_NAME
            )
        ),
    )

    forum = ModelChoiceField(
        widget=HiddenInput(),
        queryset=None,
    )

    content = CharField(widget=MarkdownEditorInlineWidget)

    class Meta:
        model = ForumTopic
        fields = ("forum", "creator", "subject", "kind", "content")

    def __init__(self, *args, forum, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["forum"].queryset = Forum.objects.filter(id=forum.id)
        self.fields["forum"].initial = forum

        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["creator"].initial = user

        if not user.has_perm(
            "discussion_forums.create_sticky_and_announcement_topic", forum
        ):
            self.fields["kind"].choices = [
                (TopicKindChoices.DEFAULT.name, TopicKindChoices.DEFAULT.label)
            ]

    def save(self, commit=True):
        topic = super().save()
        ForumPost.objects.create(
            topic=topic,
            creator=self.cleaned_data["creator"],
            content=self.cleaned_data["content"],
        )
        return topic
