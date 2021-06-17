from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.blogs.filters import BlogFilter
from grandchallenge.blogs.forms import PostForm, PostUpdateForm
from grandchallenge.blogs.models import Post
from grandchallenge.core.filters import FilterMixin


class AuthorFormKwargsMixin:
    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        author_pks = {self.request.user.pk}

        if self.object:
            author_pks.add(*[a.pk for a in self.object.authors.all()])

        authors = get_user_model().objects.filter(pk__in=author_pks)

        form_kwargs.update({"authors": authors})
        return form_kwargs


class PostCreate(PermissionRequiredMixin, AuthorFormKwargsMixin, CreateView):
    model = Post
    form_class = PostForm
    permission_required = "blogs.add_post"


class PostList(FilterMixin, ListView):
    model = Post
    filter_class = BlogFilter
    queryset = Post.objects.filter(published=True)


class PostDetail(DetailView):
    model = Post

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.prefetch_related(
            "authors__user_profile", "authors__verification"
        )
        return qs


class PostUpdate(PermissionRequiredMixin, AuthorFormKwargsMixin, UpdateView):
    model = Post
    form_class = PostUpdateForm
    permission_required = "blogs.change_post"
