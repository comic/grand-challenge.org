from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.patients.forms import PatientForm
from grandchallenge.patients.models import Patient
from grandchallenge.subdomains.utils import reverse


class PatientCreateView(UserIsStaffMixin, CreateView):
    model = Patient
    form_class = PatientForm

    def get_success_url(self):
        return reverse("patients:list")


class PatientDetailView(UserIsStaffMixin, DetailView):
    model = Patient


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
