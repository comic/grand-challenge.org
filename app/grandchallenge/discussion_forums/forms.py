from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import CharField, HiddenInput, ModelChoiceField, ModelForm

from grandchallenge.core.forms import SaveFormInitMixin
from grandchallenge.core.guardian import filter_by_permission
from grandchallenge.core.widgets import MarkdownEditorInlineWidget
from grandchallenge.discussion_forums.models import (
    Forum,
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)
from grandchallenge.subdomains.utils import reverse


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
        queryset=(
            get_user_model().objects.exclude(
                username=settings.ANONYMOUS_USER_NAME
            )
        ),
    )

    topic = ModelChoiceField(
        widget=HiddenInput(),
        queryset=None,
    )

    content = CharField(widget=MarkdownEditorInlineWidget)

    class Meta:
        model = ForumPost
        fields = ("topic", "creator", "content")

    def __init__(self, *args, topic, user, is_update=False, **kwargs):
        super().__init__(*args, **kwargs)

        self._user = user
        self._topic = topic

        self.fields["topic"].queryset = filter_by_permission(
            queryset=ForumTopic.objects.filter(pk=topic.pk),
            user=user,
            codename="view_forumtopic",
        )
        self.fields["topic"].initial = topic

        self.fields["creator"].queryset = get_user_model().objects.filter(
            pk=user.pk
        )
        self.fields["creator"].initial = user

        if is_update:
            hx_post_url = reverse(
                "discussion-forums:post-update",
                kwargs={
                    "challenge_short_name": topic.forum.parent_object.short_name,
                    "slug": self._topic.slug,
                    "pk": self.instance.pk,
                },
            )
        else:
            hx_post_url = reverse(
                "discussion-forums:post-create",
                kwargs={
                    "challenge_short_name": topic.forum.parent_object.short_name,
                    "slug": self._topic.slug,
                },
            )

        self.helper.attrs.update(
            {
                "hx-post": hx_post_url,
                "hx-target": "body",
                "hx-swap": "outerHTML",
            }
        )


class ForumTopicLockUpdateForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["is_locked"].widget = HiddenInput()

    class Meta:
        model = ForumTopic
        fields = ("is_locked",)
