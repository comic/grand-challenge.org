from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView

from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.discussion_forums.forms import TopicForm
from grandchallenge.discussion_forums.models import Topic


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
    permission_required = "view_topic"
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.object.forum})
        return context
