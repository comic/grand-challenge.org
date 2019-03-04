from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.patients.forms import PatientCreateForm, PatientUpdateForm
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class PatientTable(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        queryset = Patient.objects.all()
        worklist = self.request.query_params.get("worklist", None)

        if worklist is not None:
            queryset = queryset.filter(study__image__worklist=worklist)
            queryset = queryset.distinct();

        return queryset


class PatientRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PatientCreateView(UserIsStaffMixin, CreateView):
    model = Patient
    form_class = PatientCreateForm

    def get_success_url(self):
        return reverse("patients:patient-display")


class PatientRemoveView(UserIsStaffMixin, DeleteView):
    model = Patient
    template_name = "patients/patient_remove_form.html"

    def get_success_url(self):
        return reverse("patients:patient-display")


class PatientUpdateView(UserIsStaffMixin, UpdateView):
    model = Patient
    form_class = PatientUpdateForm

    def get_success_url(self):
        return reverse("patients:patient-display")


class PatientDisplayView(UserIsStaffMixin, ListView):
    model = Patient
    paginate_by = 100
    template_name = "patients/patient_display_form.html"
