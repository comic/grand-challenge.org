from django.views.generic import DetailView, ListView

from grandchallenge.blogs.filters import BlogFilter
from grandchallenge.blogs.models import Post
from grandchallenge.core.filters import FilterMixin


class PostList(FilterMixin, ListView):
    model = Post
    filter_class = BlogFilter

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(published=True)
        return qs


class PostDetail(DetailView):
    model = Post

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.prefetch_related(
            "authors__user_profile", "authors__verification"
        )
        return qs
