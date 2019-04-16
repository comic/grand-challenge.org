from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.models import Worklist
from grandchallenge.worklists.forms import WorklistForm


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistDetailView(UserIsStaffMixin, DetailView):
    model = Worklist
    form_class = WorklistForm


class WorklistDeleteView(UserIsStaffMixin, DeleteView):
    model = Worklist

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistForm

    def get_success_url(self):
        return reverse("worklists:list")


class WorklistListView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
