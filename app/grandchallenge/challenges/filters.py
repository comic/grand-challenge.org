from functools import reduce
from operator import or_

from django.db.models import Q
from django_filters import CharFilter, FilterSet

from grandchallenge.challenges.forms import ChallengeFilterForm
from grandchallenge.challenges.models import Challenge


class ChallengeFilter(FilterSet):
    search = CharFilter(method="search_filter", label="Search Challenges")

    class Meta:
        model = Challenge
        fields = ("search",)
        form = ChallengeFilterForm

    def search_filter(self, queryset, name, value):
        search_fields = [
            "title",
            "short_name",
            "description",
            "event_name",
        ]
        return queryset.filter(
            reduce(
                or_,
                [Q(**{f"{f}__icontains": value}) for f in search_fields],
                Q(),
            )
        )
