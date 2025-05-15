from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import CharField, HiddenInput, ModelChoiceField, ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
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
                (
                    ForumTopicKindChoices.DEFAULT.name,
                    ForumTopicKindChoices.DEFAULT.label,
                )
            ]

    def save(self, commit=True):
        topic = super().save()
        ForumPost.objects.create(
            topic=topic,
            creator=self.cleaned_data["creator"],
            content=self.cleaned_data["content"],
        )
        return topic


class ForumPostForm(SaveFormInitMixin, ModelForm):
    creator = ModelChoiceField(
        widget=HiddenInput(),
        queryset=None,
    )

    topic = ModelChoiceField(
        widget=HiddenInput(),
        queryset=None,
    )

    class Meta:
        model = ForumPost
        fields = ("topic", "creator", "content")

    def __init__(self, *args, topic, user, **kwargs):
        super().__init__(*args, **kwargs)

        self._user = user
        self._topic = topic

        self.fields["topic"].queryset = ForumTopic.objects.filter(id=topic.id)
        self.fields["topic"].initial = topic

        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["creator"].initial = user

    def clean(self):
        if (
            self._topic.is_locked
            and not self._topic.forum.parent_object.is_admin(self._user)
        ):
            # challenge admins can still post to locked topics
            raise ValidationError(
                "You can no longer reply to this topic because it is locked."
            )
