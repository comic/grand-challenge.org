from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, ListView
from guardian.mixins import LoginRequiredMixin

from grandchallenge.publications.forms import PublicationForm
from grandchallenge.publications.models import Publication
from grandchallenge.subdomains.utils import reverse


class PublicationList(LoginRequiredMixin, ListView):
    model = Publication
    paginate_by = 50

    def get_queryset(self):
        return super().get_queryset().order_by("-created")

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        num_citations = 0
        for pub in Publication.objects.all():
            num_citations += pub.referenced_by_count
        context.update(
            {
                "num_publications": Publication.objects.all().count(),
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
