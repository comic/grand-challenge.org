from django.views.generic import ListView, CreateView, DetailView, UpdateView

from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.workstations.forms import WorkstationForm
from grandchallenge.workstations.models import Workstation


class WorkstationList(UserIsStaffMixin, ListView):
    model = Workstation


class WorkstationCreate(UserIsStaffMixin, CreateView):
    model = Workstation
    form_class = WorkstationForm


class WorkstationDetail(UserIsStaffMixin, DetailView):
    model = Workstation


class WorkstationUpdate(UserIsStaffMixin, UpdateView):
    model = Workstation
    form_class = WorkstationForm
