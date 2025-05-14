from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.discussion_forums.forms import ForumTopicForm
from grandchallenge.discussion_forums.models import (
    ForumTopic,
    TopicKindChoices,
)
from grandchallenge.subdomains.utils import reverse


class ForumTopicListView(PermissionListMixin, ListView):
    model = ForumTopic
    permission_required = "discussion_forums.view_topic"
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
                    kind=TopicKindChoices.ANNOUNCE
                ),
                "default_topics": self.object_list.exclude(
                    kind=TopicKindChoices.ANNOUNCE
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
    permission_required = "discussion_forums.view_topic"
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
    permission_required = "discussion_forums.delete_topic"
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
