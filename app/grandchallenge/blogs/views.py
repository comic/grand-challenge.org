from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from grandchallenge.blogs.filters import BlogFilter
from grandchallenge.blogs.forms import (
    AuthorsForm,
    PostContentUpdateForm,
    PostForm,
    PostMetaDataUpdateForm,
)
from grandchallenge.blogs.models import Post
from grandchallenge.core.filters import FilterMixin
from grandchallenge.core.guardian import ObjectPermissionRequiredMixin
from grandchallenge.groups.views import UserGroupUpdateMixin
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class AuthorFormKwargsMixin:
    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)

        author_pks = {self.request.user.pk}

        if self.object:
            author_pks.update({a.pk for a in self.object.authors.all()})

        authors = get_user_model().objects.filter(pk__in=author_pks)

        form_kwargs.update({"authors": authors})
        return form_kwargs


class PostCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AuthorFormKwargsMixin,
    CreateView,
):
    model = Post
    form_class = PostForm
    permission_required = "blogs.add_post"
    raise_exception = True

    def get_success_url(self):
        """On successful creation, go to content update."""
        return reverse(
            "blogs:content-update",
            kwargs={
                "slug": self.object.slug,
            },
        )


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


class PostMetaDataUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    AuthorFormKwargsMixin,
    UpdateView,
):
    model = Post
    form_class = PostMetaDataUpdateForm
    permission_required = "blogs.change_post"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class PostContentUpdate(
    LoginRequiredMixin,
    ObjectPermissionRequiredMixin,
    UpdateView,
):
    model = Post
    form_class = PostContentUpdateForm
    template_name = "blogs/post_content_update.html"
    permission_required = "blogs.change_post"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class AuthorsUpdate(UserGroupUpdateMixin):
    model = Post
    form_class = AuthorsForm
    template_name = "blogs/authors_update_form.html"
    permission_required = "blogs.change_post"
    success_message = "Authors successfully updated"

    @property
    def obj(self):
        return get_object_or_404(Post, slug=self.kwargs["slug"])
