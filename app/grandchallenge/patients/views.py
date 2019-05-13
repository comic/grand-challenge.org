from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework.viewsets import ReadOnlyModelViewSet

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.patients.forms import PatientForm
from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.subdomains.utils import reverse


class PatientCreate(UserIsStaffMixin, CreateView):
    model = Patient
    form_class = PatientForm

    def get_success_url(self):
        return reverse("patients:list")


class PatientDetail(UserIsStaffMixin, DetailView):
    model = Patient


class PatientDelete(UserIsStaffMixin, DeleteView):
    model = Patient

    def get_success_url(self):
        return reverse("patients:list")


class PatientUpdate(UserIsStaffMixin, UpdateView):
    model = Patient
    form_class = PatientForm

    def get_success_url(self):
        return reverse("patients:list")


class PatientList(UserIsStaffMixin, ListView):
    model = Patient


class PatientViewSet(ReadOnlyModelViewSet):
    serializer_class = PatientSerializer
    queryset = Patient.objects.all()

    def get_queryset(self):
        filters = {
            "study__image__worklist": self.request.query_params.get(
                "worklist", None
            ),
            "study__image__files__image_type": self.request.query_params.get(
                "image_type", None
            ),
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        queryset = super().get_queryset().filter(**filters).distinct()

        return queryset
