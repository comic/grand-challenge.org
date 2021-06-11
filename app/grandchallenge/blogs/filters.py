from django_filters import FilterSet, ModelMultipleChoiceFilter
from django_select2.forms import Select2MultipleWidget

from grandchallenge.blogs.models import Post, Tag
from grandchallenge.core.filters import FilterForm


class BlogFilter(FilterSet):
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(), widget=Select2MultipleWidget, label="Tags",
    )

    class Meta:
        model = Post
        form = FilterForm
        fields = ("tags",)
