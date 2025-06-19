from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from grandchallenge.core.guardian import (
    ObjectPermissionRequiredMixin,
    ViewObjectPermissionListMixin,
    filter_by_permission,
)
from grandchallenge.discussion_forums.forms import (
    ForumPostForm,
    ForumTopicForm,
    ForumTopicLockUpdateForm,
)
from grandchallenge.discussion_forums.models import (
    ForumPost,
    ForumTopic,
    ForumTopicKindChoices,
    TopicReadRecord,
)
from grandchallenge.subdomains.utils import reverse


class ForumTopicListView(
    ObjectPermissionRequiredMixin, ViewObjectPermissionListMixin, ListView
):
    model = ForumTopic
    permission_required = "view_forum"
    raise_exception = True
    common_select_related_fields = [
        "forum",
        "creator__verification",
        "creator__user_profile",
        "last_post__creator__user_profile",
        "last_post__creator__verification",
    ]
    queryset = ForumTopic.objects.exclude(kind=ForumTopicKindChoices.ANNOUNCE)
    paginate_by = 15

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    def get_permission_object(self):
        return self.forum

    @cached_property
    def user_records(self):
        return TopicReadRecord.objects.filter(user=self.request.user)

    @property
    def common_prefetch_related_fields(self):
        return [
            "posts",
            Prefetch(
                "read_by",
                queryset=self.user_records,
                to_attr="user_read_records",
            ),
        ]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related(*self.common_select_related_fields)
            .prefetch_related(*self.common_prefetch_related_fields)
        )
        return queryset.filter(forum=self.forum)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        # we're only paginating sticky and default topics
        # announcements always stay at the top, unpaginated, so retrieve
        # these here separately
        announcements = filter_by_permission(
            queryset=ForumTopic.objects.filter(
                kind=ForumTopicKindChoices.ANNOUNCE, forum=self.forum
            )
            .select_related(*self.common_select_related_fields)
            .prefetch_related(*self.common_prefetch_related_fields),
            user=self.request.user,
            codename="view_forumtopic",
        )
        context.update(
            {
                "announcements": announcements,
                "forum": self.forum,
            }
        )
        return context


class ForumTopicCreate(ObjectPermissionRequiredMixin, CreateView):
    model = ForumTopic
    permission_required = "create_forum_topic"
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


class ForumTopicPostList(
    ObjectPermissionRequiredMixin, ViewObjectPermissionListMixin, ListView
):
    model = ForumPost
    paginate_by = 10
    permission_required = "view_forumtopic"
    raise_exception = True
    queryset = ForumPost.objects.select_related(
        "topic__forum__linked_challenge",
        "creator__user_profile",
        "creator__verification",
    )

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    @cached_property
    def topic(self):
        return get_object_or_404(
            ForumTopic,
            forum=self.forum,
            slug=self.kwargs["slug"],
        )

    @cached_property
    def unread_posts_by_user(self):
        return self.topic.get_unread_topic_posts_for_user(
            user=self.request.user
        )

    def get_permission_object(self):
        return self.topic

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(topic=self.topic)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update(
            {
                "forum": self.forum,
                "topic": self.topic,
                "post_create_form": ForumPostForm(
                    user=self.request.user, topic=self.topic
                ),
                "unread_posts_by_user": self.unread_posts_by_user,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        if self.unread_posts_by_user.exists():
            response = HttpResponseRedirect(
                self.unread_posts_by_user.first().get_absolute_url()
            )
        else:
            response = super().get(request, *args, **kwargs)
        self.topic.mark_as_read(user=self.request.user)
        return response


class ForumTopicDelete(ObjectPermissionRequiredMixin, DeleteView):
    model = ForumTopic
    permission_required = "delete_forumtopic"
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


class ForumTopicLockUpdate(ObjectPermissionRequiredMixin, UpdateView):
    model = ForumTopic
    permission_required = "lock_forumtopic"
    raise_exception = True
    form_class = ForumTopicLockUpdateForm

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
        return self.object.get_absolute_url()


class ForumPostCreate(ObjectPermissionRequiredMixin, CreateView):
    model = ForumPost
    permission_required = "create_topic_post"
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
        kwargs.update(
            {"user": self.request.user, "topic": self.topic, "instance": None}
        )
        return kwargs


class ForumPostDelete(ObjectPermissionRequiredMixin, DeleteView):
    model = ForumPost
    permission_required = "delete_forumpost"
    raise_exception = True
    success_message = "Successfully deleted post."

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    @cached_property
    def topic(self):
        return get_object_or_404(
            ForumTopic, forum=self.forum, slug=self.object.topic.slug
        )

    def get_object(self, queryset=None):
        return get_object_or_404(
            ForumPost,
            topic__forum=self.forum,
            pk=self.kwargs["pk"],
        )

    def get_success_url(self):
        if self.object.is_alone:
            return reverse(
                "discussion-forums:topic-list",
                kwargs={
                    "challenge_short_name": self.request.challenge.short_name
                },
            )
        else:
            return self.topic.get_absolute_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.forum})
        return context


class ForumPostUpdate(ObjectPermissionRequiredMixin, UpdateView):
    model = ForumPost
    permission_required = "change_forumpost"
    raise_exception = True
    form_class = ForumPostForm

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    @cached_property
    def topic(self):
        return get_object_or_404(
            ForumTopic, forum=self.forum, slug=self.object.topic.slug
        )

    def get_object(self, queryset=None):
        return get_object_or_404(
            ForumPost,
            topic__forum=self.forum,
            pk=self.kwargs["pk"],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "user": self.request.user,
                "topic": self.topic,
                "is_update": True,
            }
        )
        return kwargs


class MyForumPosts(ViewObjectPermissionListMixin, ListView):
    model = ForumPost
    paginate_by = 10

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "topic__forum__linked_challenge",
                "creator__user_profile",
                "creator__verification",
            )
            .filter(creator=self.request.user)
        )

    @cached_property
    def forum(self):
        return self.request.challenge.discussion_forum

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context.update({"forum": self.forum, "topic": None})
        return context
