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
