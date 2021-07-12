from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, ListView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.core.filters import FilterMixin
from grandchallenge.publications.filters import PublicationFilter
from grandchallenge.publications.forms import PublicationForm
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse


class PublicationList(LoginRequiredMixin, FilterMixin, ListView):
    model = Publication
    paginate_by = 50
    filter_class = PublicationFilter

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .prefetch_related(
                "algorithm_set",
                "archive_set",
                "readerstudy_set",
                "challenge_set",
                "externalchallenge_set",
            )
            .order_by("-created")
        )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        num_citations = 0
        for pub in context["object_list"]:
            try:
                num_citations += pub.referenced_by_count
            except TypeError:
                continue
        context.update(
            {
                "num_publications": context["object_list"].count(),
                "num_citations": num_citations,
            }
        )
        return context


class PublicationCreate(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    SuccessMessageMixin,
    CreateView,
):
    model = Publication
    form_class = PublicationForm
    permission_required = "publications.add_publication"
    success_message = "Publication successfully added"

    def get_success_url(self):
        return reverse("publications:list")
