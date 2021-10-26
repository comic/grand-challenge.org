from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.postgres.search import (
    SearchHeadline,
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
)
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.documentation.forms import (
    DocPageCreateForm,
    DocPageUpdateForm,
)
from grandchallenge.documentation.models import DocPage
from grandchallenge.subdomains.utils import reverse_lazy


class DocPageList(ListView):
    model = DocPage


class DocPageDetail(DetailView):
    model = DocPage

    def get_context_object_name(self, obj):
        return "currentdocpage"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        top_level_pages = (
            DocPage.objects.filter(parent__isnull=True)
            .prefetch_related("children__children")
            .order_by("order")
            .all()
        )

        qs = DocPage.objects.all()
        keywords = self.request.GET.get("query")

        if keywords:
            query = SearchQuery(keywords)
            vector = SearchVector("title", "content")
            headline = SearchHeadline("content", query)
            qs = (
                qs.annotate(headline=headline)
                .annotate(rank=SearchRank(vector, query))
                .annotate(
                    similarity=TrigramSimilarity("title", keywords)
                    + TrigramSimilarity("content", keywords)
                )
                .annotate(combined_score=(F("similarity") + F("rank")) / 2)
                .filter(Q(rank__gt=0.001) | Q(similarity__gt=0.1))
                .order_by("-combined_score")
            )
        else:
            qs = None

        context.update(
            {
                "top_level_pages": top_level_pages,
                "search_results": qs,
                "query": keywords,
            }
        )

        return context


class DocumentationHome(DocPageDetail):
    def get_object(self, queryset=None):
        return get_object_or_404(DocPage, order=1)


class DocPageUpdate(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView,
):
    model = DocPage
    form_class = DocPageUpdateForm
    permission_required = "documentation.change_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.position(form.cleaned_data["position"])
        return response


class DocPageCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView,
):
    model = DocPage
    form_class = DocPageCreateForm
    permission_required = "documentation.add_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")
