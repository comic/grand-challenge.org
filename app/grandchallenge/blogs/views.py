from django.db.models import Q
from django.views.generic import DetailView, ListView

from grandchallenge.blogs.models import Post


class PostList(ListView):
    model = Post

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(published=True)
        return qs


class PostTagList(ListView):
    model = Post

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.filter(Q(published=True) & Q(tags__slug=self.kwargs["slug"]))
        return qs


class PostDetail(DetailView):
    model = Post

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.prefetch_related(
            "authors__user_profile", "authors__verification"
        )
        return qs
