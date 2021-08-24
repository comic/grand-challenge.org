from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.views.generic import CreateView, ListView
from guardian.core import ObjectPermissionChecker

from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
from grandchallenge.challenges.models import Challenge, ExternalChallenge
from grandchallenge.core.filters import FilterMixin
from grandchallenge.publications.filters import PublicationFilter
from grandchallenge.publications.forms import PublicationForm
from grandchallenge.publications.models import Publication
from grandchallenge.reader_studies.models import ReaderStudy
from grandchallenge.subdomains.utils import reverse


class PublicationList(FilterMixin, ListView):
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

        checker = ObjectPermissionChecker(user_or_group=self.request.user)
        for qs in [
            Archive.objects.only("pk").all(),
            ReaderStudy.objects.only("pk").all(),
            Challenge.objects.only("pk").all(),
            Algorithm.objects.only("pk").all(),
            ExternalChallenge.objects.only("pk").all(),
        ]:
            # Perms can only be prefetched for sets of the same objects
            checker.prefetch_perms(objects=qs)

        context.update(
            {
                "checker": checker,
                "num_citations": self.get_queryset()
                .exclude(referenced_by_count__isnull=True)
                .aggregate(Sum("referenced_by_count"))[
                    "referenced_by_count__sum"
                ],
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
