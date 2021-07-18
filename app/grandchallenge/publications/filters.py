from django_filters import CharFilter, Filter, FilterSet

from grandchallenge.core.filters import FilterForm
from grandchallenge.publications.models import Publication


class AuthorFilter(Filter):
    def filter(self, qs, value):
        if value:
            pub_list = [
                row.id
                for row in qs
                if value.casefold() in str(row.authors).casefold()
            ]
            return qs.filter(pk__in=pub_list)
        else:
            return qs


class PublicationFilter(FilterSet):
    year = CharFilter(label="Year",)
    authors = AuthorFilter(label="Author last name")

    class Meta:
        model = Publication
        form = FilterForm
        fields = ("year",)
        search_fields = ("year", "authors")
