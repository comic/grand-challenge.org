from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.patients.forms import PatientForm
from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializers import PatientSerializer
from grandchallenge.subdomains.utils import reverse


class PatientTable(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        queryset = Patient.objects.all()
        image_type = self.request.query_params.get("image_type", None)
        worklist = self.request.query_params.get("worklist", None)

        if worklist is not None:
            queryset = queryset.filter(study__image__worklist=worklist)

        if image_type is not None:
            queryset = queryset.filter(
                study__image__files__image_type=image_type
            )

        queryset = queryset.distinct()
        return queryset


class PatientRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PatientCreateView(UserIsStaffMixin, CreateView):
    model = Patient
    form_class = PatientForm

    def get_success_url(self):
        return reverse("patients:list")


class PatientDeleteView(UserIsStaffMixin, DeleteView):
    model = Patient

    def get_success_url(self):
        return reverse("patients:list")


class PatientUpdateView(UserIsStaffMixin, UpdateView):
    model = Patient
    form_class = PatientForm

    def get_success_url(self):
        return reverse("patients:list")


class PatientListView(UserIsStaffMixin, ListView):
    model = Patient
    paginate_by = 100
