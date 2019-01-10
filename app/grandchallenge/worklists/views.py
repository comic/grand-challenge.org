from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.worklists.models import Worklist, WorklistSet
from grandchallenge.worklists.serializer import (
    WorklistSerializer,
    WorklistSetSerializer,
)
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

""" Worklist """


class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistCreateForm

    def get_success_url(self):
        return reverse("worklists:worklist-display")


class WorklistRemoveView(UserIsStaffMixin, DeleteView):
    model = Worklist
    template_name = "worklists/worklist_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:worklist-display")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistUpdateForm

    def get_success_url(self):
        return reverse("worklists:worklist-display")


class WorklistDisplayView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
    template_name = "worklists/worklist_display_form.html"


""" Worklist Set """


class WorklistSetTable(generics.ListCreateAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetCreateView(UserIsStaffMixin, CreateView):
    model = WorklistSet
    form_class = WorklistSetCreateForm

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetRemoveView(UserIsStaffMixin, DeleteView):
    model = WorklistSet
    template_name = "worklists/worklistset_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetUpdateView(UserIsStaffMixin, UpdateView):
    model = WorklistSet
    form_class = WorklistSetUpdateForm

    def get_success_url(self):
        return reverse("worklists:set-display")


class WorklistSetDisplayView(UserIsStaffMixin, ListView):
    model = WorklistSet
    paginate_by = 100
    template_name = "worklists/worklistset_display_form.html"
