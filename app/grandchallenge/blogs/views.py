from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.blogs.filters import BlogFilter
from grandchallenge.blogs.forms import PostForm
from grandchallenge.blogs.models import Post
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.forms import UserFormKwargsMixin


class PostCreate(UserFormKwargsMixin, CreateView):
    model = Post
    form_class = PostForm


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


class PostUpdate(UserFormKwargsMixin, UpdateView):
    model = Post
    form_class = PostForm
