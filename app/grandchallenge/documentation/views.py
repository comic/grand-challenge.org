from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.postgres.search import (
    SearchHeadline,
    SearchQuery,
    SearchRank,
    TrigramSimilarity,
)
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.documentation.forms import (
    DocPageContentUpdateForm,
    DocPageCreateForm,
    DocPageMetadataUpdateForm,
)
from grandchallenge.documentation.models import DocPage
from grandchallenge.subdomains.utils import reverse, reverse_lazy


class DocPageList(ListView):
    model = DocPage


class DocPageDetail(DetailView):
    model = DocPage

    def get_context_object_name(self, obj):
        return "currentdocpage"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        top_level_pages = (
            DocPage.objects.filter(
                parent__isnull=True, is_faq=self.object.is_faq
            )
            .prefetch_related("children__children__children__children")
            .order_by("order")
        )

        keywords = self.request.GET.get("query")

        if keywords:
            query = SearchQuery(keywords)
            headline = SearchHeadline("content_plain", query)
            search_results = (
                DocPage.objects.annotate(
                    headline=headline,
                    rank=SearchRank(F("search_vector"), query),
                    similarity=TrigramSimilarity("title", keywords)
                    + TrigramSimilarity("content_plain", keywords),
                )
                .annotate(combined_score=(F("similarity") + F("rank")) / 2)
                .filter(Q(rank__gt=0.001) | Q(similarity__gt=0.1))
                .order_by("-combined_score")
            )
        else:
            search_results = None

        context.update(
            {
                "top_level_pages": top_level_pages,
                "search_results": search_results,
                "query": keywords,
            }
        )
        return context


class DocumentationHome(DocPageDetail):
    def get_object(self, queryset=None):
        return get_object_or_404(DocPage, order=1)


class DocPageMetadataUpdate(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = DocPage
    form_class = DocPageMetadataUpdateForm
    permission_required = "documentation.change_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.position(form.cleaned_data["position"])
        return response


class DocPageContentUpdate(
    LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = DocPage
    form_class = DocPageContentUpdateForm
    template_name_suffix = "_content_update"
    permission_required = "documentation.change_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")


class DocPageCreate(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DocPage
    form_class = DocPageCreateForm
    permission_required = "documentation.add_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")

    def get_success_url(self):
        """On successful creation, go to content update."""
        return reverse(
            "documentation:content-update",
            kwargs={
                "slug": self.object.slug,
            },
        )
