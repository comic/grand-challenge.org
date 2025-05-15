from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.discussion_forums.forms import (
    ForumPostForm,
    ForumTopicForm,
)
from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
)
from grandchallenge.subdomains.utils import reverse


class ForumTopicListView(PermissionListMixin, ListView):
    model = ForumTopic
    permission_required = "discussion_forums.view_forumtopic"
    queryset = ForumTopic.objects.select_related("forum")

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(forum=self.forum)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                "announcements": self.object_list.filter(
                    kind=ForumTopicKindChoices.ANNOUNCE
                ),
                "default_topics": self.object_list.exclude(
                    kind=ForumTopicKindChoices.ANNOUNCE
                ),
                "forum": self.forum,
            }
        )
        return context


class ForumTopicCreate(ObjectPermissionRequiredMixin, CreateView):
    model = ForumTopic
    permission_required = "discussion_forums.create_forum_topic"
    raise_exception = True
    form_class = ForumTopicForm

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    def get_permission_object(self):
        return self.forum

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.forum})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "forum": self.forum})
        return kwargs


class ForumTopicDetail(ObjectPermissionRequiredMixin, DetailView):
    model = ForumTopic
    permission_required = "discussion_forums.view_forumtopic"
    raise_exception = True

    def get_object(self, queryset=None):
        return get_object_or_404(
            ForumTopic,
            forum=self.request.challenge.discussion_forum,
            slug=self.kwargs["slug"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.object.forum})
        return context


class ForumTopicDelete(ObjectPermissionRequiredMixin, DeleteView):
    model = ForumTopic
    permission_required = "discussion_forums.delete_forumtopic"
    raise_exception = True
    success_message = "Successfully deleted topic."

    def get_object(self, queryset=None):
        return get_object_or_404(
            ForumTopic,
            forum=self.request.challenge.discussion_forum,
            slug=self.kwargs["slug"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.object.forum})
        return context

    def get_success_url(self):
        return reverse(
            "discussion-forums:topic-list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )


class ForumPostCreate(ObjectPermissionRequiredMixin, CreateView):
    model = ForumPost
    permission_required = "discussion_forums.create_topic_post"
    raise_exception = True
    form_class = ForumPostForm

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    @cached_property
    def topic(self):
        return get_object_or_404(
            ForumTopic, forum=self.forum, slug=self.kwargs["slug"]
        )

    def get_permission_object(self):
        return self.topic

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.forum, "topic": self.topic})
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "topic": self.topic})
        return kwargs


class ForumPostDetail(ObjectPermissionRequiredMixin, DetailView):
    model = ForumPost
    permission_required = "discussion_forums.view_forumpost"
    raise_exception = True

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    @cached_property
    def topic(self):
        return get_object_or_404(
            ForumTopic, forum=self.forum, slug=self.kwargs["slug"]
        )

    def get_object(self, queryset=None):
        return get_object_or_404(
            ForumPost,
            topic=self.topic,
            pk=self.kwargs["pk"],
        )
