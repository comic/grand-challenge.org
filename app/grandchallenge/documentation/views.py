from django.contrib.auth.mixins import PermissionRequiredMixin
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

        context.update({"top_level_pages": top_level_pages})

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
        self.object.move(form.cleaned_data["move"])
        return response


class DocPageCreate(
    LoginRequiredMixin, PermissionRequiredMixin, CreateView,
):
    model = DocPage
    form_class = DocPageCreateForm
    permission_required = "documentation.add_docpage"
    raise_exception = True
    login_url = reverse_lazy("account_login")
