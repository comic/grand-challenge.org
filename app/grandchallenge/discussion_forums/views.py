from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    PermissionListMixin,
)
from grandchallenge.discussion_forums.forms import TopicForm
from grandchallenge.discussion_forums.models import Topic, TopicKindChoices
from grandchallenge.subdomains.utils import reverse


class TopicListView(PermissionListMixin, ListView):
    model = Topic
    permission_required = "discussion_forums.view_topic"
    queryset = Topic.objects.select_related("forum")

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
                    type=TopicKindChoices.ANNOUNCE
                ),
                "default_topics": self.object_list.exclude(
                    type=TopicKindChoices.ANNOUNCE
                ),
                "forum": self.forum,
            }
        )
        return context


class TopicCreate(ObjectPermissionRequiredMixin, CreateView):
    model = Topic
    permission_required = "discussion_forums.create_forum_topic"
    raise_exception = True
    form_class = TopicForm

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


class TopicDetail(ObjectPermissionRequiredMixin, DetailView):
    model = Topic
    permission_required = "discussion_forums.view_topic"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.object.forum})
        return context


class TopicDelete(ObjectPermissionRequiredMixin, DeleteView):
    model = Topic
    permission_required = "discussion_forums.delete_topic"
    raise_exception = True
    success_message = "Successfully deleted topic."

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.object.forum})
        return context

    def get_success_url(self):
        return reverse(
            "discussion-forums:topic-list",
            kwargs={"challenge_short_name": self.request.challenge.short_name},
        )
