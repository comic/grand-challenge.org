from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.studies.forms import StudyForm
from grandchallenge.studies.models import Study
from grandchallenge.studies.serializers import StudySerializer
from grandchallenge.subdomains.utils import reverse


class StudyCreateView(UserIsStaffMixin, CreateView):
    model = Study
    form_class = StudyForm

    def get_success_url(self):
        return reverse("studies:list")


class StudyDetailView(UserIsStaffMixin, DetailView):
    model = Study


class StudyDeleteView(UserIsStaffMixin, DeleteView):
    model = Study

    def get_success_url(self):
        return reverse("studies:list")


class StudyUpdateView(UserIsStaffMixin, UpdateView):
    model = Study
    form_class = StudyForm

    def get_success_url(self):
        return reverse("studies:list")


class StudyListView(UserIsStaffMixin, ListView):
    model = Study
    paginate_by = 100


class StudyViewSet(ReadOnlyModelViewSet):
    serializer_class = StudySerializer
    queryset = Study.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()

        if "patient" in self.request.query_params:
            queryset = queryset.filter(
                patient=self.request.query_params["patient"]
            )

        return queryset
