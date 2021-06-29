from functools import reduce
from operator import or_

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
