from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from rest_framework import generics

from grandchallenge.worklists.models import Worklist, WorklistSet
from grandchallenge.worklists.serializer import WorklistSerializer, WorklistSetSerializer
from grandchallenge.core.urlresolvers import reverse
from grandchallenge.core.permissions.mixins import UserIsStaffMixin
from grandchallenge.worklists.forms import (WorklistCreateForm,
                                            WorklistUpdateForm,
                                            WorklistSetCreateForm,
                                            WorklistSetUpdateForm)


## Worklist ###
class WorklistTable(generics.ListCreateAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = Worklist.objects.all()
    serializer_class = WorklistSerializer


class WorklistCreate(UserIsStaffMixin, CreateView):
    model = Worklist
    form_class = WorklistCreateForm

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistUpdate(UserIsStaffMixin, UpdateView):
    model = Worklist
    form_class = WorklistUpdateForm

    def get_success_url(self):
        return reverse("worklists:set_list")


class WorklistDelete(UserIsStaffMixin, DeleteView):
    model = Worklist
    template_name = 'worklists/worklist_deletion_form.html'

    def get_success_url(self):
        return reverse("worklists:set-list")


class WorklistList(UserIsStaffMixin, ListView):
    model = Worklist
    paginate_by = 100
    template_name = 'worklists/worklist_list_form.html'


### Worklist Set ###
class WorklistSetTable(generics.ListCreateAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetRecord(generics.RetrieveUpdateDestroyAPIView):
    queryset = WorklistSet.objects.all()
    serializer_class = WorklistSetSerializer


class WorklistSetCreate(UserIsStaffMixin, CreateView):
    model = WorklistSet
    form_class = WorklistSetCreateForm

    def get_success_url(self):
        return reverse("worklists:set-list")


class WorklistSetUpdate(UserIsStaffMixin, UpdateView):
    model = WorklistSet
    form_class = WorklistSetUpdateForm

    def get_success_url(self):
        return reverse("worklists:set-list")


class WorklistSetDelete(UserIsStaffMixin, DeleteView):
    model = WorklistSet
    template_name = 'worklists/worklistset_deletion_form.html'

    def get_success_url(self):
        return reverse("worklists:set-list")


class WorklistSetList(UserIsStaffMixin, ListView):
    model = WorklistSet
    paginate_by = 100
    template_name = 'worklists/worklistset_list_form.html'
