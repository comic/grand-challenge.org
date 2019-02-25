from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics
from grandchallenge.subdomains.utils import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.models import Worklist, WorklistSet
from grandchallenge.worklists.serializers import (
    WorklistSerializer,
    WorklistSetSerializer,
)
from grandchallenge.worklists.forms import (
    WorklistCreateForm,
    WorklistUpdateForm,
    WorklistSetCreateForm,
    WorklistSetUpdateForm,
)

""" Worklist API Endpoints """


class WorklistTable(generics.ListCreateAPIView):
    serializer_class = WorklistSerializer

    def get_queryset(self):
        queryset = Worklist.objects.filter(set__user=self.request.user)
        return queryset


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


""" WorklistSet API Endpoints """


class WorklistSetTable(generics.ListCreateAPIView):
    serializer_class = WorklistSetSerializer

    def get_queryset(self):
        queryset = WorklistSet.objects.filter(user=self.request.user)
        return queryset


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


""" Worklist Forms Views """


class WorklistCreateView(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistCreateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistRemoveView(UserIsStaffMixin, DeleteView):
    model = Worklist
    template_name = "worklists/worklist_remove_form.html"

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistUpdateView(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistUpdateForm

    def get_success_url(self):
        return reverse("worklists:list-display")


class WorklistDisplayView(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
    template_name = "worklists/worklist_display_form.html"


""" WorklistSet Forms Views """


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
