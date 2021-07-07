from django_filters import CharFilter, FilterSet

from grandchallenge.core.filters import FilterForm
from grandchallenge.publications.models import Publication


class PublicationFilter(FilterSet):
    year = CharFilter(label="Year",)
    authors = CharFilter(label="Author", method="search_filter",)

    class Meta:
        model = Publication
        form = FilterForm
        fields = ("year",)
        search_fields = ("year", "authors")

    def search_filter(self, queryset, name, value):
        return queryset.filter(citation__icontains=value)
