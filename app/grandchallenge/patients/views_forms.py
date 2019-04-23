from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.patients.forms import PatientForm
from grandchallenge.patients.models import Patient
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
