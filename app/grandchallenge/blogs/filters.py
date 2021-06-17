from functools import reduce
from operator import or_

from django.contrib.auth import get_user_model
from django.db.models import Q
from django_filters import CharFilter, FilterSet, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.blogs.models import Post, Tag
from grandchallenge.core.filters import FilterForm


class BlogFilter(FilterSet):
    search = CharFilter(method="search_filter", label="Title or Content")
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), widget=Select2MultipleWidget, label="Tags",
    )
    authors = ModelMultipleChoiceFilter(
        queryset=get_user_model()
        .objects.filter(
            blog_authors__isnull=False, blog_authors__published=True
        )
        .distinct()
        .order_by("username"),
        widget=Select2MultipleWidget,
        label="Authors",
    )

    class Meta:
        model = Post
        form = FilterForm
        fields = ("search", "authors", "tags")
        search_fields = ("title", "content")

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            reduce(
                or_,
                [
                    Q(**{f"{f}__icontains": value})
                    for f in self.Meta.search_fields
                ],
                Q(),
            )
        )
