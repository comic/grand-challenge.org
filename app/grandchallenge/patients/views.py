from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.patients.models import Patient
from grandchallenge.patients.serializer import PatientSerializer
from grandchallenge.patients.forms import PatientCreateForm, PatientUpdateForm
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin


class PatientTable(generics.ListCreateAPIView):
    serializer_class = PatientSerializer

    def get_queryset(self):
        # Get URL parameter as a string, if exists
        ids = self.request.query_params.get('ids', None)

        # Get snippets for ids if they exist
        if ids is not None:
            # Convert parameter string to list of integers
            ids = [int(x) for x in ids.split(',')]
            # Get objects for all parameter ids
            queryset = Patient.objects.filter(pk__in=ids)

        else:
            # Else no parameters, return all objects
            queryset = Patient.objects.all()

        return queryset


class PatientRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PatientCreate(CreateView, UserIsStaffMixin):
    model = Patient
    form_class = PatientCreateForm

    def get_success_url(self):
        return reverse("patients:patient-list")


class PatientUpdate(UpdateView, UserIsStaffMixin):
    model = Patient
    form_class = PatientUpdateForm

    def get_success_url(self):
        return reverse("patients:patient-list")


class PatientDelete(DeleteView, UserIsStaffMixin):
    model = Patient
    template_name = "patients/patient_deletion_form.html"

    def get_success_url(self):
        return reverse("patients:patient-list")


class PatientList(ListView, UserIsStaffMixin):
    model = Patient
    paginate_by = 100
    template_name = "patients/patient_list_form.html"
