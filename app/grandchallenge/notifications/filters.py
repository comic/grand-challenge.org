import re
from functools import reduce
from operator import or_

from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters import CharFilter, ChoiceFilter, FilterSet
from machina.apps.forum.models import Forum
from machina.apps.forum_conversation.models import Topic

from grandchallenge.core.filters import FilterForm
from grandchallenge.notifications.models import Notification


BOOLEAN_CHOICES = (
    ("1", "Read"),
    ("0", "Unread"),
)


class NotificationFilter(FilterSet):
    forum = CharFilter(method="search_filter", label="Forum")
    topic = CharFilter(method="search_filter", label="Forum post subject")
    read = ChoiceFilter(choices=BOOLEAN_CHOICES, label="Status")

    class Meta:
        model = Notification
        form = FilterForm
        fields = ("forum", "topic", "read")

    def search_filter(self, queryset, name, value):

        if name == "forum":
            name_qs = [
                x.id for x in Forum.objects.filter(name__icontains=value).all()
            ]
        elif name == "topic":
            name_qs = [
                x.id
                for x in Topic.objects.filter(subject__icontains=value).all()
            ]

        search_fields = (
            "action__target_object_id",
            "action__action_object_object_id",
        )

        return queryset.filter(
            reduce(
                or_, [Q(**{f"{f}__in": name_qs}) for f in search_fields], Q(),
            )
        )


FOLLOW_CHOICES = (
    ("forum_forum", "Forums"),
    ("topic_forum_conversation", "Topics"),
    ("readerstudy_reader_studies", "Reader studies"),
    ("archive_archives", "Archives"),
    ("algorithm_algorithms", "Algorithms"),
    ("challenge_challenges", "Challenges"),
    ("externalchallenge_challenges", "External Challenges"),
    ("phase_evaluation", "Challenge Phase"),
)


class FollowFilter(FilterSet):

    forum = CharFilter(method="search_filter", label="Search for a forum")
    topic = CharFilter(
        method="search_filter", label="Search for a forum topic"
    )
    forums_for_user = CharFilter(
        method="search_forum_topics",
        label="Show all topic subscriptions for a specific forum",
    )
    content_type = ChoiceFilter(
        choices=FOLLOW_CHOICES,
        method="get_content_type",
        label="Filter by subscription type",
    )

    class Meta:
        model = Follow
        form = FilterForm
        fields = ("forum", "topic", "forums_for_user", "content_type")

    def search_filter(self, queryset, name, value):
        model_name = name
        if model_name == "forum":
            app_label = "forum"
            model = Forum
            kwargs = {"name__icontains": value}
        elif model_name == "topic":
            app_label = "forum_conversation"
            model = Topic
            kwargs = {"subject__icontains": value}

        name_qs = [x.id for x in model.objects.filter(**kwargs).all()]

        return queryset.filter(
            **{"object_id__in": name_qs},
            **{
                "content_type__exact": ContentType.objects.filter(
                    model=model_name, app_label=app_label
                ).get()
            },
        )

    def search_forum_topics(self, queryset, name, value):
        forums = [
            x.id for x in Forum.objects.filter(name__icontains=value).all()
        ]
        name_qs = [
            x.id for x in Topic.objects.filter(forum__id__in=forums).all()
        ]
        return queryset.filter(
            **{"object_id__in": name_qs},
            **{
                "content_type__exact": ContentType.objects.filter(
                    model="topic", app_label="forum_conversation"
                ).get()
            },
        )

    def get_content_type(self, queryset, name, value):
        ct = ContentType.objects.filter(
            model=re.split(r"_", value, 1)[0],
            app_label=re.split(r"_", value, 1)[1],
        ).get()
        return queryset.filter(content_type__exact=ct)
